"""Score the test split once with the exported model. A guard file next to the manifest refuses a second run."""

from __future__ import annotations

import json
from pathlib import Path

from sklearn.metrics import confusion_matrix

from doodleverse.classes import LABELS
from doodleverse.data.load import load_split
from doodleverse.data.splits import read_manifest
from doodleverse.report import upsert_section
from doodleverse.tracking import log_run
from doodleverse.training.export import MODEL_FILE, SIDECAR_FILE, sha256
from doodleverse.training.gate import gate_stats
from doodleverse.training.metrics import classification_scores
from doodleverse.training.plots import save_confusion


def guard_path(manifest_path: Path) -> Path:
    return manifest_path.with_name(f"{manifest_path.stem}.test-scored.json")


def refuse_if_scored(manifest_path: Path) -> None:
    guard = guard_path(manifest_path)
    if guard.exists():
        record = json.loads(guard.read_text(encoding="utf-8"))
        raise RuntimeError(
            f"The test split of {manifest_path.name} was already scored, for model {record['model_sha256'][:12]} "
            f"({guard.as_posix()}). It is scored once."
        )


def scored_section(test: dict, sidecar: dict, guard: Path) -> str:
    validation = sidecar["validation"]
    weakest = min(test["per_class"], key=lambda row: row["recall"])
    lines = [
        "## Test split",
        "",
        f"Scored once, after the model, the gate, and the rasterizer were frozen: {test['count']:,} drawings, "
        f"none of them read before. `{guard.as_posix()}` records the result and makes a second run refuse.",
        "",
        "| split | accuracy | macro-F1 | gate coverage | accepted accuracy |",
        "| --- | --- | --- | --- | --- |",
        f"| validation | {validation['accuracy']:.3f} | {validation['macro_f1']:.3f} | "
        f"{validation['gate_coverage']:.1%} | {validation['gate_accepted_accuracy']:.3f} |",
        f"| test | {test['accuracy']:.3f} | {test['macro_f1']:.3f} | {test['gate_coverage']:.1%} | "
        f"{test['gate_accepted_accuracy']:.3f} |",
        "",
        "| class | precision | recall | f1 | support |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in test["per_class"]:
        lines.append(
            f"| {row['label']} | {row['precision']:.3f} | {row['recall']:.3f} | {row['f1']:.3f} | {row['support']} |"
        )
    lines.extend(
        [
            "",
            f"Weakest class on test: {weakest['label']} (recall {weakest['recall']:.3f}). The gate thresholds were "
            "chosen on validation, so the test row is the honest estimate of what they keep.",
            "",
            "[Test confusion](figures/test_confusion.png)",
        ]
    )
    return "\n".join(lines) + "\n"


def score_test_once(
    manifest_path: Path,
    raw_dir: Path,
    model_dir: Path,
    experiments_path: Path,
    figure_dir: Path,
    tracking_uri: Path | None = None,
) -> dict:
    import tensorflow as tf

    refuse_if_scored(manifest_path)
    sidecar_path = model_dir / SIDECAR_FILE
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    if sha256(model_dir / MODEL_FILE) != sidecar["sha256"]:
        raise RuntimeError(f"{model_dir / MODEL_FILE} does not match the SHA-256 in its sidecar.")
    manifest = read_manifest(manifest_path)
    x_test, y_test = load_split(manifest, "test", raw_dir, allow_test=True)
    model = tf.keras.models.load_model(model_dir / MODEL_FILE, compile=False)
    probs = model.predict(x_test[..., None], batch_size=256, verbose=0)
    predicted = probs.argmax(axis=1)
    scores = classification_scores(y_test, predicted, LABELS)
    stats = gate_stats(probs, y_test, sidecar["gate"]["min_score"], sidecar["gate"]["min_margin"])
    matrix = confusion_matrix(y_test, predicted, labels=list(range(len(LABELS))))
    test = {
        "count": int(len(y_test)),
        "accuracy": scores["accuracy"],
        "macro_f1": scores["macro_f1"],
        "gate_coverage": stats["coverage"],
        "gate_accepted_accuracy": stats["accepted_accuracy"],
        "per_class": scores["per_class"],
        "confusion_matrix": matrix.tolist(),
    }
    guard = guard_path(manifest_path)
    record = {
        "manifest": manifest_path.name,
        "model_sha256": sidecar["sha256"],
        "variant": sidecar["variant"],
        "count": test["count"],
        "accuracy": test["accuracy"],
        "macro_f1": test["macro_f1"],
        "gate_coverage": test["gate_coverage"],
        "gate_accepted_accuracy": test["gate_accepted_accuracy"],
    }
    with guard.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(record, indent=2) + "\n")
    sidecar["test"] = test
    sidecar_path.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")
    save_confusion(matrix, list(LABELS), figure_dir / "test_confusion.png", "CNN test, scored once")
    upsert_section(experiments_path, "Test split", scored_section(test, sidecar, guard), after="Export")
    if tracking_uri is not None:
        log_run(
            tracking_uri,
            "doodleverse-test",
            "test-once",
            {"variant": sidecar["variant"], "model_sha256": sidecar["sha256"]},
            {key: test[key] for key in ("accuracy", "macro_f1", "gate_coverage", "gate_accepted_accuracy")},
            [sidecar_path],
        )
    return test


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Score the test split once with the exported model.")
    parser.add_argument("--manifest", type=Path, default=Path("ml/splits/v1.json"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--model-dir", type=Path, default=Path("artifacts/model"))
    parser.add_argument("--experiments", type=Path, default=Path("docs/experiments.md"))
    parser.add_argument("--figure-dir", type=Path, default=Path("docs/figures"))
    parser.add_argument("--tracking-uri", type=Path, default=Path("mlruns"))
    args = parser.parse_args()
    test = score_test_once(
        args.manifest,
        args.raw_dir,
        args.model_dir,
        args.experiments,
        args.figure_dir,
        args.tracking_uri,
    )
    print(
        f"test accuracy {test['accuracy']:.3f}  macro-F1 {test['macro_f1']:.3f}  "
        f"gate coverage {test['gate_coverage']:.3f}  accepted accuracy {test['gate_accepted_accuracy']:.3f}"
    )


if __name__ == "__main__":
    main()
