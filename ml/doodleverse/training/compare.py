from __future__ import annotations

import json
import os
import platform
import shutil
import time
from pathlib import Path

import numpy as np

from doodleverse.data.splits import read_manifest
from doodleverse.report import upsert_section
from doodleverse.training.train_baseline import load_train_and_val, run_baseline
from doodleverse.training.train_cnn import run_cnn


def per_class_table(rows: list[dict]) -> str:
    lines = ["| class | precision | recall | f1 | support |", "| --- | --- | --- | --- | --- |"]
    for row in rows:
        lines.append(
            f"| {row['label']} | {row['precision']:.3f} | {row['recall']:.3f} | "
            f"{row['f1']:.3f} | {row['support']} |"
        )
    return "\n".join(lines)


def weakest_class(report: dict) -> dict:
    return min(report["per_class"], key=lambda row: row["recall"])


def warm_latency_ms(model, images: np.ndarray, warmup: int = 10, repeats: int = 100) -> dict:
    """Single-image forward passes after a warmup. The first call pays graph tracing."""

    first = np.asarray(images[0], dtype=np.float32).reshape(1, 28, 28, 1)
    started = time.perf_counter()
    model(first, training=False)
    cold_ms = (time.perf_counter() - started) * 1000
    for _ in range(warmup):
        model(first, training=False)
    samples = []
    for index in range(repeats):
        tensor = np.asarray(images[index % len(images)], dtype=np.float32).reshape(1, 28, 28, 1)
        started = time.perf_counter()
        model(tensor, training=False)
        samples.append((time.perf_counter() - started) * 1000)
    values = np.asarray(samples)
    return {
        "cold_ms": cold_ms,
        "mean_ms": float(values.mean()),
        "p50_ms": float(np.percentile(values, 50)),
        "p95_ms": float(np.percentile(values, 95)),
    }


def _explain(baseline: dict, cnn: dict) -> str:
    gap = cnn["val_macro_f1"] - baseline["val_macro_f1"]
    if gap > 0.01:
        return (
            f"The CNN is {gap:.3f} macro-F1 above logistic regression on validation. "
            "A convolution reuses the same local stroke detector at every position in the bitmap. "
            "Logistic regression has one weight per pixel, so a curve in the corner and the same curve "
            "in the middle need unrelated weights."
        )
    if gap < -0.01:
        return (
            f"The CNN is {abs(gap):.3f} macro-F1 below logistic regression on validation. "
            "These centered 28×28 bitmaps already give a linear model most of the class signal."
        )
    return "The two models land within 0.01 macro-F1 on validation."


def models_section(manifest: dict, baseline: dict, cnn: dict, latency: dict, tf_version: str) -> str:
    base_weak = weakest_class(baseline)
    cnn_weak = weakest_class(cnn)
    lines = [
        "## Models",
        "",
        f"Validation split only (3,600 drawings, 600 per class). The test split was not read. "
        f"Split seed {manifest['seed']}. Machine: {platform.platform()}, {os.cpu_count()} CPUs, "
        f"Python {platform.python_version()}, TensorFlow {tf_version}.",
        "",
        "Accuracy equals macro-recall here because every class has the same support.",
        "",
        "### Logistic regression",
        "",
        "Multinomial cross-entropy on the 784 flattened pixels, L2 penalty, lbfgs. "
        "One fit per C on the full training split. The best validation macro-F1 is kept.",
        "",
        "| C | val accuracy | val macro-F1 | iterations | converged |",
        "| --- | --- | --- | --- | --- |",
    ]
    for trial in baseline["c_search"]:
        lines.append(
            f"| {trial['C']} | {trial['val_accuracy']:.3f} | {trial['val_macro_f1']:.3f} | "
            f"{trial['iterations']} | {'yes' if trial['converged'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            f"Kept `C={baseline['C']}`. Train accuracy {baseline['train_accuracy']:.3f}, "
            f"validation accuracy {baseline['val_accuracy']:.3f}, macro-F1 {baseline['val_macro_f1']:.3f}. "
            f"{baseline['parameter_count']} parameters. Weakest class: {base_weak['label']} "
            f"(recall {base_weak['recall']:.3f}).",
            "",
            per_class_table(baseline["per_class"]),
            "",
            "### CNN",
            "",
            "Three 3×3 conv blocks (32, 64, 128 filters), batch norm (momentum 0.9), ReLU, max-pool after the "
            "first two, global average pooling, dropout 0.3, softmax over six classes. Adam at 1e-3, sparse "
            "categorical cross-entropy, up to 8% whole-pixel shifts during training only, learning rate halved "
            "on a validation-loss plateau, early stopping that restores the best validation-loss epoch.",
            "",
            f"Best epoch {cnn['best_epoch']} of {cnn['epochs_ran']}. Train accuracy {cnn['train_accuracy']:.3f} "
            f"(inference mode), validation accuracy {cnn['val_accuracy']:.3f}, macro-F1 {cnn['val_macro_f1']:.3f}. "
            f"{cnn['parameter_count']} parameters, {cnn['model_bytes'] / 1024:.0f} KB on disk. "
            f"Weakest class: {cnn_weak['label']} (recall {cnn_weak['recall']:.3f}).",
            "",
            f"Single-image CPU forward pass: first call {latency['cold_ms']:.1f} ms, then "
            f"p50 {latency['p50_ms']:.2f} ms and p95 {latency['p95_ms']:.2f} ms over 100 calls. "
            "This is the model alone, not the HTTP service.",
            "",
            per_class_table(cnn["per_class"]),
            "",
            _explain(baseline, cnn),
            "",
            "Figures: [baseline confusion](figures/baseline_confusion.png), "
            "[CNN learning curves](figures/cnn_learning_curves.png), "
            "[CNN confusion](figures/cnn_confusion.png).",
        ]
    )
    return "\n".join(lines) + "\n"


def publish_figures(baseline_dir: Path, cnn_dir: Path, figure_dir: Path) -> None:
    figure_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(baseline_dir / "confusion_val.png", figure_dir / "baseline_confusion.png")
    shutil.copyfile(cnn_dir / "learning_curves.png", figure_dir / "cnn_learning_curves.png")
    shutil.copyfile(cnn_dir / "confusion_val.png", figure_dir / "cnn_confusion.png")


def run_comparison(
    manifest_path: Path,
    raw_dir: Path,
    artifact_dir: Path,
    experiments_path: Path,
    figure_dir: Path,
    tracking_uri: Path,
) -> tuple[dict, dict]:
    import tensorflow as tf

    manifest = read_manifest(manifest_path)
    (x_train, y_train), (x_val, y_val) = load_train_and_val(manifest, raw_dir)
    baseline = run_baseline(x_train, y_train, x_val, y_val, artifact_dir / "baseline", tracking_uri=tracking_uri)
    cnn = run_cnn(
        x_train,
        y_train,
        x_val,
        y_val,
        artifact_dir / "cnn-gap",
        seed=manifest["seed"],
        tracking_uri=tracking_uri,
    )
    model = tf.keras.models.load_model(artifact_dir / "cnn-gap" / "model.keras")
    latency = warm_latency_ms(model, x_val[:64])
    publish_figures(artifact_dir / "baseline", artifact_dir / "cnn-gap", figure_dir)
    upsert_section(experiments_path, "Models", models_section(manifest, baseline, cnn, latency, tf.__version__))
    (artifact_dir / "comparison.json").write_text(
        json.dumps({"baseline": baseline, "cnn": cnn, "latency": latency}, indent=2),
        encoding="utf-8",
    )
    return baseline, cnn


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Train the baseline and CNN, then compare them on validation.")
    parser.add_argument("--manifest", type=Path, default=Path("ml/splits/v1.json"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--artifact-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--experiments", type=Path, default=Path("docs/experiments.md"))
    parser.add_argument("--figure-dir", type=Path, default=Path("docs/figures"))
    parser.add_argument("--tracking-uri", type=Path, default=Path("mlruns"))
    args = parser.parse_args()
    baseline, cnn = run_comparison(
        args.manifest,
        args.raw_dir,
        args.artifact_dir,
        args.experiments,
        args.figure_dir,
        args.tracking_uri,
    )
    for name, report in (("baseline", baseline), ("cnn", cnn)):
        weak = weakest_class(report)
        print(
            f"{name:8s} val accuracy {report['val_accuracy']:.3f}  macro-F1 {report['val_macro_f1']:.3f}  "
            f"weakest {weak['label']} recall {weak['recall']:.3f}"
        )


if __name__ == "__main__":
    main()
