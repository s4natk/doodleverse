"""Validation mistakes and the uncertainty gate for one trained CNN. The test split stays closed."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.metrics import confusion_matrix

from doodleverse.classes import LABELS
from doodleverse.data.load import load_split
from doodleverse.data.splits import read_manifest
from doodleverse.report import upsert_section
from doodleverse.training.errors import (
    class_ink,
    confused_pairs,
    false_positives,
    ink_ratio,
    mean_ink,
    pair_rows,
    save_mistake_gallery,
    score_summary,
)
from doodleverse.training.gate import (
    DEFAULT_TARGET,
    TARGETS,
    accept,
    calibration_error,
    choose_thresholds,
    save_coverage_curve,
)

GALLERY_PAIRS = 4

# Qualitative, checked against docs/figures/cnn_mistakes.png. Recheck when the kept model changes.
PAIR_NOTES = {
    ("tree", "flower"): "Nearly all are lollipop trees: one round or scalloped canopy on a bare trunk, which is "
    "also how a flower head on a stem is drawn. They carry about as much ink as correct trees, so the confusion "
    "is shape, not clutter.",
    ("cat", "sun"): "Whiskers drawn as short strokes pointing out from a round head look like rays around a disc. "
    "These cats carry less ink than correct ones, and the most confident are unfinished: whiskers and two dots "
    "with no head.",
    ("flower", "cat"): "Scribbled or spiky petals, and drawings that stop at a ground line with one small bump.",
    ("car", "cat"): "Side views where the wheels, windows, and body run together at 28×28.",
}


def describe(model_dir: Path) -> str:
    report = json.loads((model_dir / "metrics.json").read_text(encoding="utf-8"))
    filters = report.get("filters", [32, 64, 128])
    return f"The {report['variant']} CNN ({'/'.join(str(width) for width in filters)} filters)"


def errors_section(name: str, pairs: list[dict], summary: dict, sink: dict) -> str:
    lines = [
        "## Errors",
        "",
        f"{name} on validation: {summary['mistakes']} mistakes in {summary['total']:,} drawings. The median top-1 "
        f"score is {summary['median_score_right']:.3f} when the prediction is right and "
        f"{summary['median_score_wrong']:.3f} when it is wrong. {summary['wrong_below_0_9']:.0%} of the mistakes "
        f"score under 0.9, against {summary['right_below_0_9']:.0%} of the correct predictions. The gate below "
        "uses that gap.",
        "",
        "Ink is the mean pixel of the mistaken drawings divided by that of correctly classified drawings of the "
        "same true class.",
        "",
        "| true | predicted | count | share of the true class | ink | held back by the gate |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for pair in pairs:
        lines.append(
            f"| {pair['true']} | {pair['predicted']} | {pair['count']} | {pair['share']:.1%} | "
            f"{pair['ink']:.2f}× | {pair['held_back']} of {pair['count']} |"
        )
    lines.extend(
        [
            "",
            f"{sink['label'].capitalize()} is the most common wrong answer: {sink['count']} of the "
            f"{summary['mistakes']} mistakes are drawings of another class called {sink['label']}.",
        ]
    )
    if sink["inkiest"] and sink["ink"] > 1.0:
        lines[-1] += (
            f" Correct {sink['label']} drawings carry the most ink of the six classes, and the drawings pulled "
            f"into {sink['label']} carry {sink['ink']:.2f}× the ink of correct drawings of their own class."
        )
    for pair in pairs[:GALLERY_PAIRS]:
        note = PAIR_NOTES.get((pair["true"], pair["predicted"]))
        if note:
            lines.extend(["", f"{pair['true']} → {pair['predicted']}. {note}"])
    lines.extend(
        [
            "",
            f"[Mistake gallery](figures/cnn_mistakes.png): the top {GALLERY_PAIRS} pairs, the most confident "
            "mistakes first.",
        ]
    )
    return "\n".join(lines) + "\n"


def gate_section(rows: list[dict], chosen: dict, accuracy: float, mean_score: float, ece: float) -> str:
    lines = [
        "## Uncertainty gate",
        "",
        "A prediction is accepted when its top-1 score and its lead over the second class (the margin) both "
        "clear a threshold. Anything else goes back to the person as a top-three choice. Each row is the widest "
        "validation coverage whose accepted accuracy reaches the target, searched over a fixed grid.",
        "",
        "| target | min score | min margin | coverage | accepted accuracy | mistakes let through |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['target']} | {row['min_score']:.2f} | {row['min_margin']:.2f} | {row['coverage']:.1%} | "
            f"{row['accepted_accuracy']:.3f} | {row['errors_accepted']} of {row['errors_total']} |"
        )
    kept = (
        f"Kept: target {chosen['target']}, score at least {chosen['min_score']:.2f} and margin at least "
        f"{chosen['min_margin']:.2f}. That accepts {chosen['coverage']:.1%} of validation drawings at "
        f"{chosen['accepted_accuracy']:.3f} accuracy and lets {chosen['errors_accepted']} of "
        f"{chosen['errors_total']} mistakes through."
    )
    if chosen["min_score"] <= chosen["min_margin"]:
        kept += (
            f" The score floor does not bind: a margin of {chosen['min_margin']:.2f} already means a top-1 score "
            f"of at least {chosen['min_margin']:.2f}."
        )
    lines.extend(
        [
            "",
            kept,
            "",
            "The scores are softmax outputs, not calibrated probabilities. No calibration was fit, and a score of "
            f"0.9 is not a promise of being right 90% of the time. On validation the mean top-1 score is "
            f"{mean_score:.3f} against an accuracy of {accuracy:.3f}, and the expected calibration error over ten "
            f"bins is {ece:.3f}. That agreement is measured on bitmaps like the training ones, not promised for "
            "new drawings. The thresholds were also picked on the split they are reported on, so this coverage "
            "is optimistic.",
            "",
            "[Coverage curve](figures/gate_coverage.png)",
        ]
    )
    return "\n".join(lines) + "\n"


def run_analysis(
    manifest_path: Path,
    raw_dir: Path,
    model_dir: Path,
    artifact_dir: Path,
    experiments_path: Path,
    figure_dir: Path,
    target: float = DEFAULT_TARGET,
) -> dict:
    import tensorflow as tf

    manifest = read_manifest(manifest_path)
    x_val, y_val = load_split(manifest, "val", raw_dir)
    model = tf.keras.models.load_model(model_dir / "model.keras", compile=False)
    probs = model.predict(x_val[..., None], batch_size=256, verbose=0)
    predicted = probs.argmax(axis=1)

    rows = [choose_thresholds(probs, y_val, value) for value in TARGETS]
    chosen = choose_thresholds(probs, y_val, target)
    held = ~accept(probs, chosen["min_score"], chosen["min_margin"])
    accuracy = float((predicted == y_val).mean())
    mean_score = float(probs.max(axis=1).mean())
    ece = calibration_error(probs, y_val)

    matrix = confusion_matrix(y_val, predicted, labels=list(range(len(LABELS))))
    ink = mean_ink(x_val)
    typical = class_ink(ink, y_val, predicted, len(LABELS))
    pairs = confused_pairs(matrix, LABELS)
    for pair in pairs:
        members = pair_rows(y_val, predicted, pair["true_index"], pair["predicted_index"])
        pair["ink"] = ink_ratio(ink, typical, y_val, members)
        pair["held_back"] = int(held[members].sum())
    absorbed = false_positives(matrix)
    sink_index = int(np.argmax(absorbed))
    sink = {
        "label": LABELS[sink_index],
        "count": int(absorbed[sink_index]),
        "inkiest": int(np.argmax(typical)) == sink_index,
        "ink": ink_ratio(ink, typical, y_val, np.flatnonzero((predicted == sink_index) & (y_val != sink_index))),
    }
    summary = score_summary(y_val, probs)

    save_mistake_gallery(x_val, y_val, probs, pairs[:GALLERY_PAIRS], figure_dir / "cnn_mistakes.png")
    save_coverage_curve(probs, y_val, chosen, figure_dir / "gate_coverage.png")
    upsert_section(experiments_path, "Errors", errors_section(describe(model_dir), pairs, summary, sink))
    upsert_section(experiments_path, "Uncertainty gate", gate_section(rows, chosen, accuracy, mean_score, ece))
    gate = {
        "model_dir": model_dir.as_posix(),
        "min_score": chosen["min_score"],
        "min_margin": chosen["min_margin"],
        "target": chosen["target"],
        "val_coverage": chosen["coverage"],
        "val_accepted_accuracy": chosen["accepted_accuracy"],
        "val_calibration_error": ece,
    }
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "gate.json").write_text(json.dumps(gate, indent=2), encoding="utf-8")
    return {"pairs": pairs, "summary": summary, "gate": gate, "rows": rows}


def main() -> None:
    import argparse

    from doodleverse.training.select_cnn import kept_model_dir

    parser = argparse.ArgumentParser(description="Write the validation mistakes and the uncertainty gate.")
    parser.add_argument("--manifest", type=Path, default=Path("ml/splits/v1.json"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--model-dir", type=Path, help="Defaults to the run kept by select_cnn.")
    parser.add_argument("--artifact-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--experiments", type=Path, default=Path("docs/experiments.md"))
    parser.add_argument("--figure-dir", type=Path, default=Path("docs/figures"))
    parser.add_argument("--target", type=float, default=DEFAULT_TARGET)
    args = parser.parse_args()
    result = run_analysis(
        args.manifest,
        args.raw_dir,
        args.model_dir or kept_model_dir(args.artifact_dir),
        args.artifact_dir,
        args.experiments,
        args.figure_dir,
        args.target,
    )
    for pair in result["pairs"][:3]:
        print(f"{pair['true']} -> {pair['predicted']}: {pair['count']}, held back {pair['held_back']}")
    gate = result["gate"]
    print(
        f"gate score>={gate['min_score']:.2f} margin>={gate['min_margin']:.2f}  "
        f"coverage {gate['val_coverage']:.3f}  accepted accuracy {gate['val_accepted_accuracy']:.3f}"
    )


if __name__ == "__main__":
    main()
