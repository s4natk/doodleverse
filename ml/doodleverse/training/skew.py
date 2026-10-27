"""Score the kept CNN on held-out Quick, Draw! strokes run through the live rasterizer.

Each sampled drawing also exists as Google's 28×28 bitmap, so it is scored twice: as the bitmap the
model was trained on and as our raster of its strokes. The difference between the two is rendering.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from doodleverse.classes import LABELS
from doodleverse.data.download import bitmap_path
from doodleverse.data.ndjson import CANVAS_SIZE, read_drawings
from doodleverse.data.splits import read_manifest
from doodleverse.preprocess.bitmap import normalize_quickdraw_batch
from doodleverse.preprocess.strokes import PAD_FRACTION, STROKE_WIDTH, strokes_to_model_input
from doodleverse.preprocess.validate import SketchValidationError, validate_sketch
from doodleverse.report import upsert_section
from doodleverse.tracking import log_run
from doodleverse.training.gate import gate_stats
from doodleverse.training.metrics import classification_scores

SAMPLE_PER_CLASS = 1000
LARGE_GAP = 0.01
# The rasterizer settings this probe started from. Kept so before and after can both be rerun.
BEFORE = (18, 0.12)
WIDTHS = (10, 12, 14, 16, 18, 20)
PADS = (0.04, 0.06, 0.08, 0.10, 0.12, 0.14)


def manifest_indices(manifest: dict, label: str) -> set[int]:
    return {int(row["index"]) for rows in manifest["splits"].values() for row in rows if row["label"] == label}


def load_sample(manifest: dict, raw_dir: Path, cache_dir: Path, per_class: int) -> dict:
    """Held-out strokes plus Google's bitmap of each one. Drawings the validator rejects are dropped."""

    strokes, targets, bitmaps = [], [], []
    lines_read, rejected = {}, {}
    for target, label in enumerate(LABELS):
        drawings = read_drawings(label, per_class, manifest_indices(manifest, label), cache_dir)
        lines_read[label] = drawings[-1][0] + 1
        kept = []
        for index, drawing in drawings:
            try:
                validate_sketch(drawing, CANVAS_SIZE, CANVAS_SIZE)
            except SketchValidationError:
                continue
            kept.append((index, drawing))
        rejected[label] = len(drawings) - len(kept)
        rows = np.asarray([index for index, _ in kept], dtype=np.int64)
        stored = np.load(bitmap_path(raw_dir, label), mmap_mode="r")
        bitmaps.append(normalize_quickdraw_batch(np.asarray(stored[rows]), "ink_high"))
        strokes.extend(drawing for _, drawing in kept)
        targets.extend([target] * len(kept))
    return {
        "strokes": strokes,
        "y": np.asarray(targets, dtype=np.int64),
        "bitmaps": np.concatenate(bitmaps),
        "lines_read": lines_read,
        "rejected": rejected,
    }


def rasterize(strokes: list, stroke_width: int, pad_fraction: float) -> np.ndarray:
    tensors = [
        strokes_to_model_input(drawing, CANVAS_SIZE, CANVAS_SIZE, stroke_width, pad_fraction) for drawing in strokes
    ]
    return np.concatenate(tensors)[..., 0]


def agreement(rasters: np.ndarray, bitmaps: np.ndarray) -> dict:
    """Mean per-drawing pixel correlation and the total ink of `rasters` over `bitmaps`."""

    a = rasters.reshape(len(rasters), -1).astype(np.float64)
    b = bitmaps.reshape(len(bitmaps), -1).astype(np.float64)
    a0 = a - a.mean(axis=1, keepdims=True)
    b0 = b - b.mean(axis=1, keepdims=True)
    norms = np.linalg.norm(a0, axis=1) * np.linalg.norm(b0, axis=1)
    correlation = (a0 * b0).sum(axis=1) / np.maximum(norms, 1e-12)
    return {"correlation": float(correlation.mean()), "ink_ratio": float(a.sum() / b.sum())}


def roll_within_class(images: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Pair every drawing with the next one of the same class instead of itself."""

    rolled = images.copy()
    for label in np.unique(y):
        rows = np.flatnonzero(y == label)
        rolled[rows] = images[np.roll(rows, 1)]
    return rolled


def score(model, images: np.ndarray, y: np.ndarray, gate: dict) -> dict:
    probs = model.predict(images[..., None], batch_size=512, verbose=0)
    predicted = probs.argmax(axis=1)
    scores = classification_scores(y, predicted, LABELS)
    stats = gate_stats(probs, y, gate["min_score"], gate["min_margin"])
    true_prob = probs[np.arange(len(y)), y]
    return {
        "accuracy": scores["accuracy"],
        "macro_f1": scores["macro_f1"],
        "log_loss": float(-np.mean(np.log(np.clip(true_prob, 1e-7, 1.0)))),
        "mean_score": float(probs.max(axis=1).mean()),
        "coverage": stats["coverage"],
        "accepted_accuracy": stats["accepted_accuracy"],
    }


def evaluate(
    model,
    sample: dict,
    tune: np.ndarray,
    gate: dict,
    stroke_width: int,
    pad_fraction: float,
    images: np.ndarray | None = None,
) -> dict:
    if images is None:
        images = rasterize(sample["strokes"], stroke_width, pad_fraction)
    y = sample["y"]
    return {
        "stroke_width": stroke_width,
        "pad_fraction": pad_fraction,
        "all": score(model, images, y, gate),
        "tune": score(model, images[tune], y[tune], gate),
        "check": score(model, images[~tune], y[~tune], gate),
        **agreement(images, sample["bitmaps"]),
    }


def pick(grid: list[dict]) -> dict:
    """Best tune-half accuracy; ties go to the lower tune-half log loss."""

    return max(grid, key=lambda row: (row["tune"]["accuracy"], -row["tune"]["log_loss"]))


def save_examples(sample: dict, settings: list[tuple[str, int, float]], destination: Path, per_class: int = 2) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    columns = [int(index) for label in range(len(LABELS)) for index in np.flatnonzero(sample["y"] == label)[:per_class]]
    rows = [("Google bitmap", sample["bitmaps"][columns])]
    for name, width, pad in settings:
        rows.append((name, rasterize([sample["strokes"][index] for index in columns], width, pad)))
    figure, axes = plt.subplots(len(rows), len(columns), figsize=(len(columns) * 0.9, len(rows) * 1.05), squeeze=False)
    for row, (name, images) in enumerate(rows):
        for column, image in enumerate(images):
            axis = axes[row, column]
            axis.imshow(image, cmap="gray", vmin=0, vmax=1)
            axis.set_xticks([])
            axis.set_yticks([])
            if row == 0:
                axis.set_title(LABELS[sample["y"][columns[column]]], fontsize=7)
            if column == 0:
                axis.set_ylabel(name, rotation=0, ha="right", va="center", fontsize=7)
    figure.suptitle("The same held-out drawings: Google's bitmap and our raster of the strokes", fontsize=9)
    figure.tight_layout()
    figure.savefig(destination, dpi=140)
    plt.close(figure)


def _setting(row: dict) -> str:
    return f"width {row['stroke_width']}, pad {row['pad_fraction']:.2f}"


def skew_section(summary: dict) -> str:
    before, shipped, bitmaps = summary["before"], summary["shipped"], summary["bitmaps"]
    lines = [
        "## Stroke skew",
        "",
        "The CNN trains on Google's bitmaps. The app sends strokes, which `strokes_to_model_input` rasterizes. "
        f"To measure the difference, the first {summary['per_class']:,} drawings per class whose line index is "
        "not in the split manifest were streamed from the simplified ndjson files, stopping once enough had "
        f"arrived: {summary['lines_read']:,} lines read, {summary['skipped']} skipped as manifest rows, "
        f"{summary['rejected']} rejected by the sketch validator.",
        "",
        "Line i of an ndjson file is row i of the bitmap file. With the starting settings, our raster of a "
        f"drawing correlates {summary['alignment']['same']:.2f} with bitmap row i and "
        f"{summary['alignment']['other']:.2f} with the next drawing of the same class. So every drawing below is "
        "scored twice, as Google's bitmap and as our raster of the same strokes, and the difference is rendering "
        "alone.",
        "",
        "| input | accuracy | macro-F1 | mean top-1 score | gate coverage | accepted accuracy |",
        "| --- | --- | --- | --- | --- | --- |",
        f"| validation bitmaps | {summary['validation_accuracy']:.3f} | {summary['validation_macro_f1']:.3f} | "
        f"{summary['gate']['val_mean_score']:.3f} | {summary['gate']['val_coverage']:.1%} | "
        f"{summary['gate']['val_accepted_accuracy']:.3f} |",
    ]
    rows = [("sample, Google's bitmaps", bitmaps), (f"sample, our raster, {_setting(before)}", before["all"])]
    if shipped["stroke_width"] != before["stroke_width"] or shipped["pad_fraction"] != before["pad_fraction"]:
        rows.append((f"sample, our raster, {_setting(shipped)}", shipped["all"]))
    for name, row in rows:
        lines.append(
            f"| {name} | {row['accuracy']:.3f} | {row['macro_f1']:.3f} | {row['mean_score']:.3f} | "
            f"{row['coverage']:.1%} | {row['accepted_accuracy']:.3f} |"
        )
    gap = bitmaps["accuracy"] - before["all"]["accuracy"]
    lines.extend(
        [
            "",
            f"With {_setting(before)}, our raster scored {gap:.3f} accuracy below Google's bitmaps of the same "
            f"drawings and carried {before['ink_ratio']:.2f}× their ink (pixel correlation "
            f"{before['correlation']:.3f}).",
        ]
    )
    if summary["grid"]:
        chosen = summary["chosen"]
        lines.extend(
            [
                "",
                f"That is more than the {LARGE_GAP} allowed, so stroke width (pixels on the 256 canvas) and pad "
                "fraction were searched on this sample only: chosen by accuracy on the even-numbered drawings, "
                "reported on the odd-numbered ones. Validation and test bitmaps were not used.",
                "",
                "Tune-half accuracy:",
                "",
                "| width | " + " | ".join(f"pad {pad:.2f}" for pad in PADS) + " |",
                "| --- |" + " --- |" * len(PADS),
            ]
        )
        by_setting = {(row["stroke_width"], row["pad_fraction"]): row for row in summary["grid"]}
        for width in WIDTHS:
            cells = [f"{by_setting[(width, pad)]['tune']['accuracy']:.3f}" for pad in PADS]
            lines.append(f"| {width} | " + " | ".join(cells) + " |")
        check_bitmaps = summary["bitmaps_check"]
        lines.extend(
            [
                "",
                f"Chosen: {_setting(chosen)}. On the held-back odd half, accuracy went from "
                f"{before['check']['accuracy']:.3f} to {chosen['check']['accuracy']:.3f}, against "
                f"{check_bitmaps['accuracy']:.3f} for Google's bitmaps of the same drawings. Ink went from "
                f"{before['ink_ratio']:.2f}× to {chosen['ink_ratio']:.2f}× and pixel correlation from "
                f"{before['correlation']:.3f} to {chosen['correlation']:.3f}.",
            ]
        )
        if (chosen["stroke_width"], chosen["pad_fraction"]) == (shipped["stroke_width"], shipped["pad_fraction"]):
            lines.extend(
                [
                    "",
                    f"`STROKE_WIDTH` and `PAD_FRACTION` in `preprocess/strokes.py` now ship as {_setting(shipped)}, "
                    "and the golden stroke fixture is rendered with them.",
                ]
            )
        else:
            lines.extend(["", f"The shipped settings ({_setting(shipped)}) are not the chosen ones."])
    lines.extend(
        [
            "",
            "These are simplified strokes from the dataset, already smoothed and resampled by Google. Pointer events "
            "from a browser are denser and noisier, so this measures rendering, not the whole path from a live "
            "sketch.",
            "",
            "[Examples](figures/skew_examples.png): Google's bitmap above our rasters of the same strokes.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_skew(
    manifest_path: Path,
    raw_dir: Path,
    cache_dir: Path,
    model_dir: Path,
    gate_path: Path,
    artifact_dir: Path,
    experiments_path: Path,
    figure_dir: Path,
    tracking_uri: Path | None,
    per_class: int = SAMPLE_PER_CLASS,
) -> dict:
    import tensorflow as tf

    manifest = read_manifest(manifest_path)
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    report = json.loads((model_dir / "metrics.json").read_text(encoding="utf-8"))
    model = tf.keras.models.load_model(model_dir / "model.keras", compile=False)
    sample = load_sample(manifest, raw_dir, cache_dir, per_class)
    y = sample["y"]
    tune = np.arange(len(y)) % 2 == 0

    before_images = rasterize(sample["strokes"], *BEFORE)
    before = evaluate(model, sample, tune, gate, *BEFORE, images=before_images)
    same = before["correlation"]
    other = agreement(before_images, roll_within_class(sample["bitmaps"], y))["correlation"]
    bitmaps = score(model, sample["bitmaps"], y, gate)
    gap = bitmaps["accuracy"] - before["all"]["accuracy"]

    grid = []
    if gap > LARGE_GAP:
        for width in WIDTHS:
            for pad in PADS:
                grid.append(before if (width, pad) == BEFORE else evaluate(model, sample, tune, gate, width, pad))
    chosen = pick(grid) if grid else before
    by_setting = {(row["stroke_width"], row["pad_fraction"]): row for row in [before, *grid]}
    shipped = by_setting.get((STROKE_WIDTH, PAD_FRACTION)) or evaluate(
        model, sample, tune, gate, STROKE_WIDTH, PAD_FRACTION
    )

    summary = {
        "per_class": per_class,
        "lines_read": int(sum(sample["lines_read"].values())),
        "skipped": int(sum(sample["lines_read"].values()) - len(y) - sum(sample["rejected"].values())),
        "rejected": int(sum(sample["rejected"].values())),
        "alignment": {"same": same, "other": other},
        "validation_accuracy": report["val_accuracy"],
        "validation_macro_f1": report["val_macro_f1"],
        "gate": gate,
        "bitmaps": bitmaps,
        "bitmaps_check": score(model, sample["bitmaps"][~tune], y[~tune], gate),
        "before": before,
        "chosen": chosen,
        "shipped": shipped,
        "grid": grid,
    }
    settings = [(f"ours, {_setting(before)}", *BEFORE)]
    if (shipped["stroke_width"], shipped["pad_fraction"]) != BEFORE:
        settings.append((f"ours, {_setting(shipped)}", STROKE_WIDTH, PAD_FRACTION))
    save_examples(sample, settings, figure_dir / "skew_examples.png")
    upsert_section(experiments_path, "Stroke skew", skew_section(summary))
    out_dir = artifact_dir / "skew"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if tracking_uri is not None:
        log_run(
            tracking_uri,
            "doodleverse-skew",
            "stroke-probe",
            {
                "per_class": per_class,
                "model_dir": model_dir.as_posix(),
                "before": _setting(before),
                "shipped": _setting(shipped),
            },
            {
                "bitmap_accuracy": bitmaps["accuracy"],
                "before_accuracy": before["all"]["accuracy"],
                "shipped_accuracy": shipped["all"]["accuracy"],
                "shipped_check_accuracy": shipped["check"]["accuracy"],
            },
            [out_dir / "summary.json"],
        )
    return summary


def main() -> None:
    import argparse

    from doodleverse.training.select_cnn import kept_model_dir

    parser = argparse.ArgumentParser(description="Score the kept CNN on held-out strokes through the rasterizer.")
    parser.add_argument("--manifest", type=Path, default=Path("ml/splits/v1.json"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--cache-dir", type=Path, default=Path("data/strokes"))
    parser.add_argument("--model-dir", type=Path, help="Defaults to the run kept by select_cnn.")
    parser.add_argument("--artifact-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--experiments", type=Path, default=Path("docs/experiments.md"))
    parser.add_argument("--figure-dir", type=Path, default=Path("docs/figures"))
    parser.add_argument("--tracking-uri", type=Path, default=Path("mlruns"))
    parser.add_argument("--per-class", type=int, default=SAMPLE_PER_CLASS)
    args = parser.parse_args()
    summary = run_skew(
        args.manifest,
        args.raw_dir,
        args.cache_dir,
        args.model_dir or kept_model_dir(args.artifact_dir),
        args.artifact_dir / "gate.json",
        args.artifact_dir,
        args.experiments,
        args.figure_dir,
        args.tracking_uri,
        args.per_class,
    )
    print(
        f"bitmaps {summary['bitmaps']['accuracy']:.3f}  "
        f"raster {_setting(summary['before'])} {summary['before']['all']['accuracy']:.3f}  "
        f"raster {_setting(summary['shipped'])} {summary['shipped']['all']['accuracy']:.3f}"
    )
    if summary["grid"]:
        chosen = summary["chosen"]
        print(f"chosen {_setting(chosen)}  check-half accuracy {chosen['check']['accuracy']:.3f}")


if __name__ == "__main__":
    main()
