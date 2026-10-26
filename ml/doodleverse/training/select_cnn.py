"""Train the narrow CNN and keep one of the two: higher validation macro-F1, then lower latency."""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from doodleverse.data.splits import read_manifest
from doodleverse.models.cnn import CNN_VARIANTS
from doodleverse.report import upsert_section
from doodleverse.training.train_baseline import load_train_and_val
from doodleverse.training.train_cnn import run_cnn

CANDIDATES = ("gap", "narrow")
F1_TOLERANCE = 0.005
LATENCY_REPEATS = 300


def run_dir(artifact_dir: Path, variant: str) -> Path:
    return artifact_dir / f"cnn-{variant}"


def kept_model_dir(artifact_dir: Path) -> Path:
    """The selected run, or the gap CNN before any selection was made."""

    selection = artifact_dir / "selection.json"
    if selection.exists():
        return Path(json.loads(selection.read_text(encoding="utf-8"))["model_dir"])
    return run_dir(artifact_dir, "gap")


def trained_report(directory: Path, variant: str) -> dict | None:
    """The saved report when it was trained with the current settings for this variant."""

    path = directory / "metrics.json"
    if not path.exists():
        return None
    report = json.loads(path.read_text(encoding="utf-8"))
    matches = (
        report.get("variant") == variant
        and report.get("filters", list(CNN_VARIANTS["gap"])) == list(CNN_VARIANTS[variant])
        and report.get("bn_momentum") == 0.9
        and report.get("interpolation") == "nearest"
    )
    return report if matches else None


def interleaved_latency(models: dict, images: np.ndarray, warmup: int = 20, repeats: int = LATENCY_REPEATS) -> dict:
    """Single-image forward passes. The models take turns, so drift on the machine hits both alike."""

    tensors = [np.asarray(image, dtype=np.float32).reshape(1, 28, 28, 1) for image in images]
    for model in models.values():
        for _ in range(warmup):
            model(tensors[0], training=False)
    samples: dict[str, list[float]] = {name: [] for name in models}
    order = list(models.items())
    for index in range(repeats):
        tensor = tensors[index % len(tensors)]
        for name, model in order if index % 2 == 0 else order[::-1]:
            started = time.perf_counter()
            model(tensor, training=False)
            samples[name].append((time.perf_counter() - started) * 1000)
    return {
        name: {"p50_ms": float(np.percentile(values, 50)), "p95_ms": float(np.percentile(values, 95))}
        for name, values in samples.items()
    }


def choose(candidates: list[dict], tolerance: float = F1_TOLERANCE) -> tuple[dict, str]:
    """Highest macro-F1. Anything within `tolerance` of it competes on warm p50 instead."""

    best = max(candidates, key=lambda item: item["val_macro_f1"])
    close = [item for item in candidates if best["val_macro_f1"] - item["val_macro_f1"] <= tolerance]
    kept = min(close, key=lambda item: item["p50_ms"])
    others = [item for item in candidates if item is not kept]
    if len(close) == 1:
        lead = min(kept["val_macro_f1"] - item["val_macro_f1"] for item in others)
        return kept, f"Its macro-F1 is {lead:.3f} higher, more than the {tolerance} tolerance."
    slower = min((item for item in close if item is not kept), key=lambda item: item["p50_ms"])
    return kept, (
        f"Macro-F1 is within {tolerance} ({abs(kept['val_macro_f1'] - slower['val_macro_f1']):.3f} apart), so "
        f"latency decides: warm p50 {kept['p50_ms']:.2f} ms against {slower['p50_ms']:.2f} ms."
    )


def narrow_section(rows: list[dict], kept: dict, reason: str) -> str:
    lines = [
        "## Narrow CNN",
        "",
        "The same blocks at half the width (16, 32, 64 filters), trained with the same fixed settings, split, and "
        f"seed. Rule: keep the higher validation macro-F1; within {F1_TOLERANCE}, keep the one with the lower warm "
        f"p50. Latency is {LATENCY_REPEATS} single-image CPU forward passes per model after a warmup, the two "
        "models taking turns on the same inputs.",
        "",
        "| variant | filters | parameters | best epoch | val accuracy | val macro-F1 | warm p50 | warm p95 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['variant']} | {'/'.join(str(width) for width in row['filters'])} | "
            f"{row['parameter_count']:,} | {row['best_epoch']} of {row['epochs_ran']} | {row['val_accuracy']:.3f} | "
            f"{row['val_macro_f1']:.3f} | {row['p50_ms']:.2f} ms | {row['p95_ms']:.2f} ms |"
        )
    lines.extend(["", f"Kept: {kept['variant']}. {reason}"])
    small = min(rows, key=lambda row: row["parameter_count"])
    large = max(rows, key=lambda row: row["parameter_count"])
    if small is not large and abs(small["p50_ms"] - large["p50_ms"]) < 0.05 * large["p50_ms"]:
        lines.extend(
            [
                "",
                f"{small['variant'].capitalize()} has {large['parameter_count'] / small['parameter_count']:.1f}× "
                f"fewer parameters but the same single-image latency within 5% ({small['p50_ms']:.2f} against "
                f"{large['p50_ms']:.2f} ms). At batch size 1 on this CPU, per-call overhead sets the time, not the "
                "convolutions.",
            ]
        )
    for row in rows:
        if row["best_epoch"] == row["epochs_ran"]:
            lines.extend(
                [
                    "",
                    f"The {row['variant']} run's best epoch was its last ({row['epochs_ran']}), so it was still "
                    "improving when the shared schedule ended. Both models get the same budget here.",
                ]
            )
    return "\n".join(lines) + "\n"


def run_selection(
    manifest_path: Path,
    raw_dir: Path,
    artifact_dir: Path,
    experiments_path: Path,
    tracking_uri: Path,
) -> dict:
    import tensorflow as tf

    manifest = read_manifest(manifest_path)
    (x_train, y_train), (x_val, y_val) = load_train_and_val(manifest, raw_dir)
    reports = {}
    for variant in CANDIDATES:
        directory = run_dir(artifact_dir, variant)
        report = trained_report(directory, variant)
        if report is None:
            report = run_cnn(
                x_train,
                y_train,
                x_val,
                y_val,
                directory,
                seed=manifest["seed"],
                tracking_uri=tracking_uri,
                variant=variant,
            )
        reports[variant] = report
    models = {
        variant: tf.keras.models.load_model(run_dir(artifact_dir, variant) / "model.keras", compile=False)
        for variant in CANDIDATES
    }
    latency = interleaved_latency(models, x_val[:64])
    rows = []
    for variant in CANDIDATES:
        report = reports[variant]
        rows.append(
            {
                "variant": variant,
                "filters": list(CNN_VARIANTS[variant]),
                "parameter_count": report["parameter_count"],
                "best_epoch": report["best_epoch"],
                "epochs_ran": report["epochs_ran"],
                "val_accuracy": report["val_accuracy"],
                "val_macro_f1": report["val_macro_f1"],
                **latency[variant],
            }
        )
    kept, reason = choose(rows)
    selection = {
        "variant": kept["variant"],
        "model_dir": run_dir(artifact_dir, kept["variant"]).as_posix(),
        "reason": reason,
        "candidates": rows,
    }
    (artifact_dir / "selection.json").write_text(json.dumps(selection, indent=2), encoding="utf-8")
    upsert_section(experiments_path, "Narrow CNN", narrow_section(rows, kept, reason), after="CNN training fixes")
    return selection


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Train the narrow CNN and keep one of the two.")
    parser.add_argument("--manifest", type=Path, default=Path("ml/splits/v1.json"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--artifact-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--experiments", type=Path, default=Path("docs/experiments.md"))
    parser.add_argument("--tracking-uri", type=Path, default=Path("mlruns"))
    args = parser.parse_args()
    selection = run_selection(args.manifest, args.raw_dir, args.artifact_dir, args.experiments, args.tracking_uri)
    for row in selection["candidates"]:
        print(
            f"{row['variant']:7s} macro-F1 {row['val_macro_f1']:.3f}  p50 {row['p50_ms']:.2f} ms  "
            f"params {row['parameter_count']}"
        )
    print(f"kept {selection['variant']}: {selection['reason']}")


if __name__ == "__main__":
    main()
