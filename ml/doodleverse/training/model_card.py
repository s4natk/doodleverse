"""Write docs/model-card.md from the exported sidecar and the runs that chose the model, gate, and rasterizer."""

from __future__ import annotations

import json
from pathlib import Path

from doodleverse.classes import LABELS
from doodleverse.data.splits import read_manifest

SOURCES = (
    "artifacts/model/sidecar.json",
    "artifacts/gate.json",
    "artifacts/skew/summary.json",
    "artifacts/comparison.json",
    "ml/splits/v1.json",
)


def top_confusions(matrix: list[list[int]], count: int = 3) -> list[tuple[str, str, int]]:
    """The largest off-diagonal cells of a confusion matrix whose rows are true classes."""

    cells = [
        (LABELS[true], LABELS[predicted], value)
        for true, row in enumerate(matrix)
        for predicted, value in enumerate(row)
        if true != predicted and value > 0
    ]
    return sorted(cells, key=lambda cell: -cell[2])[:count]


def _per_class(rows: list[dict]) -> list[str]:
    lines = ["| class | precision | recall | f1 | support |", "| --- | --- | --- | --- | --- |"]
    for row in rows:
        lines.append(
            f"| {row['label']} | {row['precision']:.3f} | {row['recall']:.3f} | {row['f1']:.3f} | {row['support']} |"
        )
    return lines


def model_card(sidecar: dict, gate: dict, skew: dict, comparison: dict, manifest: dict) -> str:
    test, validation, raster = sidecar["test"], sidecar["validation"], sidecar["rasterizer"]
    if test is None:
        raise ValueError("The sidecar has no test score yet. Run doodleverse.training.score_test_split first.")
    version = f"{sidecar['variant']}-{sidecar['sha256'][:12]}"
    splits = {name: len(rows) for name, rows in manifest["splits"].items()}
    git = sidecar["git"]
    built = f"commit `{git['commit'][:7]}`" if git.get("commit") else "an unknown commit"
    if git.get("dirty"):
        built += " with uncommitted changes in the tree"
    confusions = ", ".join(f"{true} → {predicted} ({count})" for true, predicted, count in top_confusions(
        test["confusion_matrix"]
    ))
    weakest = min(test["per_class"], key=lambda row: row["recall"])
    baseline = comparison["baseline"]
    before, chosen = skew["before"], skew["chosen"]
    filters = "/".join(str(width) for width in sidecar["filters"])
    lines = [
        "# Model card",
        "",
        "Written by `python -m doodleverse.training.model_card` from "
        + ", ".join(f"`{source}`" for source in SOURCES)
        + ". How each number was reached is in [experiments.md](experiments.md).",
        "",
        "## Model",
        "",
        f"`{version}` names one doodle as one of six classes: {', '.join(LABELS)}. It is a small convolutional "
        f"network: three 3×3 convolution blocks ({filters} filters) with batch norm and ReLU, max-pooling after "
        "the first two, global average pooling, dropout 0.3, and a six-way softmax. "
        f"{sidecar['parameter_count']:,} parameters, {sidecar['file_bytes'] / 1024:,.0f} KB as `model.keras`, "
        f"SHA-256 `{sidecar['sha256'][:12]}…`.",
        "",
        f"Trained and exported with TensorFlow {sidecar['tensorflow']} and Keras {sidecar['keras']}, from "
        f"{built}.",
        "",
        f"Input: one {sidecar['input']['size']}×{sidecar['input']['size']} grayscale image, float32 in [0, 1], "
        f"ink bright on dark (`{sidecar['input']['polarity']}`). The app sends strokes, and the service draws them "
        f"into that image itself: a {raster['raster_size']}-pixel canvas, stroke width {raster['stroke_width']}, "
        f"pad {raster['pad_fraction']:.2f}, then an area resize to 28×28.",
        "",
        "Output: six scores that sum to 1, the top three, and `uncertain`, which is true unless the top score "
        f"leads the second by at least {sidecar['gate']['min_margin']:.2f}.",
        "",
        "## Intended use",
        "",
        "Naming a simple drawing in a drawing toy, where the person confirms or corrects every answer before "
        "anything happens. An uncertain answer is never acted on: the person picks the class.",
        "",
        "Not for decisions with consequences, for photos or handwriting, or for judging how well someone draws. It "
        "knows no class outside the six and always answers with one of them.",
        "",
        "## Data",
        "",
        "Quick, Draw! by Google Creative Lab, used under CC BY 4.0: the 28×28 bitmaps Google rendered from players' "
        f"strokes. {manifest['samples_per_class']:,} drawings per class, split with seed {manifest['seed']} into "
        f"{splits['train']:,} for training, {splits['val']:,} for validation, and {splits['test']:,} for test, "
        "with the same number of every class in each split. The players drew in the online game from many "
        "countries. No breakdown by country was made.",
        "",
        "## Results",
        "",
        "| split | drawings | accuracy | macro-F1 | gate coverage | accepted accuracy |",
        "| --- | --- | --- | --- | --- | --- |",
        f"| validation | {splits['val']:,} | {validation['accuracy']:.3f} | {validation['macro_f1']:.3f} | "
        f"{validation['gate_coverage']:.1%} | {validation['gate_accepted_accuracy']:.3f} |",
        f"| test | {test['count']:,} | {test['accuracy']:.3f} | {test['macro_f1']:.3f} | "
        f"{test['gate_coverage']:.1%} | {test['gate_accepted_accuracy']:.3f} |",
        "",
        "The test split was scored once, after the model, the gate, and the rasterizer were frozen. Gate coverage is "
        "the share of drawings answered without asking; accepted accuracy is how often those answers were right.",
        "",
        "Per class on test:",
        "",
        *_per_class(test["per_class"]),
        "",
        f"Weakest class: {weakest['label']} (recall {weakest['recall']:.3f}). The most common test mistakes, true → "
        f"predicted: {confusions}.",
        "",
        f"For comparison, logistic regression on the same pixels reached {baseline['val_macro_f1']:.3f} validation "
        f"macro-F1 (C={baseline['C']}).",
        "",
        "## Scores and the gate",
        "",
        f"The gate's margin of {sidecar['gate']['min_margin']:.2f} was chosen on validation as the widest coverage "
        f"whose accepted accuracy reaches {sidecar['gate']['target']}. The score floor of "
        f"{sidecar['gate']['min_score']:.2f} does not bind.",
        "",
        "The scores are softmax outputs, not calibrated probabilities. On validation the mean top score was "
        f"{gate['val_mean_score']:.3f} against an accuracy of {validation['accuracy']:.3f}, and the expected "
        f"calibration error over ten bins was {gate['val_calibration_error']:.3f}. No calibration was fit.",
        "",
        "## Strokes, not bitmaps",
        "",
        "The model learned from Google's renders, but the app's drawings are rasterized by this project. To measure "
        f"that gap, {skew['per_class'] * len(LABELS):,} drawings ({skew['per_class']:,} per class) that are not in "
        "the split were read from Google's simplified stroke files and scored twice: as Google's bitmap, and as "
        "this rasterizer's drawing of the same strokes.",
        "",
        "| input | accuracy on the held-back half |",
        "| --- | --- |",
        f"| Google's bitmaps | {skew['bitmaps_check']['accuracy']:.3f} |",
        f"| our raster, width {before['stroke_width']}, pad {before['pad_fraction']:.2f} | "
        f"{before['check']['accuracy']:.3f} |",
        f"| our raster, width {chosen['stroke_width']}, pad {chosen['pad_fraction']:.2f} (shipped) | "
        f"{chosen['check']['accuracy']:.3f} |",
        "",
        "Width and pad were chosen on the other half of those drawings, not on validation or test. They are Google's "
        "simplified strokes, already smoothed and resampled. Pointer input from a browser is denser and noisier, and "
        "its accuracy was not measured.",
        "",
        "## Limitations",
        "",
        "- Six classes. A drawing of anything else still gets one of the six. The gate holds back close calls, but it "
        "was never tested on drawings outside the six.",
        "- One training run on one split with one seed. No rerun measured how far these numbers move.",
        "- The gate was tuned on validation, so its validation coverage is optimistic. The test row is the honest one.",
        "- Live drawings were not scored against labels; the stroke gap above is for dataset strokes.",
        "- Latency depends on the machine. Measured numbers, with the hardware, are in "
        "[benchmark-results.md](benchmark-results.md).",
        "",
        "## Privacy",
        "",
        "The service keeps nothing it is sent. Each prediction logs the label, score, uncertain flag, stroke and point "
        "counts, and latency, never the points.",
        "",
    ]
    return "\n".join(lines)


def write_model_card(artifact_dir: Path, manifest_path: Path, out: Path) -> str:
    def read(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    card = model_card(
        read(artifact_dir / "model" / "sidecar.json"),
        read(artifact_dir / "gate.json"),
        read(artifact_dir / "skew" / "summary.json"),
        read(artifact_dir / "comparison.json"),
        read_manifest(manifest_path),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(card, encoding="utf-8")
    return card


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Write the model card from the exported model and its runs.")
    parser.add_argument("--artifact-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--manifest", type=Path, default=Path("ml/splits/v1.json"))
    parser.add_argument("--out", type=Path, default=Path("docs/model-card.md"))
    args = parser.parse_args()
    write_model_card(args.artifact_dir, args.manifest, args.out)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
