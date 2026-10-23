"""Look at the six bitmap files before any model is trained.

The figures and docs/experiments.md are written from measurements. Polarity
is decided from the mean pixel in the files, not from a description of the
dataset.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from doodleverse.classes import LABELS
from doodleverse.data.download import bitmap_path, bitmap_row_count
from doodleverse.preprocess.bitmap import decide_polarity

PROBE_ROWS = 2048
CHUNK = 8192


def _load_probe(path: Path, rows: int, seed: int) -> np.ndarray:
    stored = np.load(path, mmap_mode="r")
    count = int(stored.shape[0])
    take = min(rows, count)
    rng = np.random.default_rng(seed)
    indices = np.sort(rng.choice(count, size=take, replace=False))
    return np.asarray(stored[indices], dtype=np.uint8).reshape(take, 28, 28)


def _ink_counts(path: Path) -> np.ndarray:
    stored = np.load(path, mmap_mode="r")
    counts = np.empty(int(stored.shape[0]), dtype=np.int32)
    for start in range(0, counts.size, CHUNK):
        block = np.asarray(stored[start : start + CHUNK])
        counts[start : start + block.shape[0]] = np.count_nonzero(block, axis=1)
    return counts


def measure(raw_dir: Path, seed: int = 1729) -> dict:
    classes = []
    probes = []
    for offset, label in enumerate(LABELS):
        path = bitmap_path(raw_dir, label)
        probe = _load_probe(path, PROBE_ROWS, seed + offset)
        probes.append(probe)
        ink = probe > 0
        border = np.concatenate(
            [
                ink[:, :2, :].reshape(-1),
                ink[:, -2:, :].reshape(-1),
                ink[:, 2:-2, :2].reshape(-1),
                ink[:, 2:-2, -2:].reshape(-1),
            ]
        )
        classes.append(
            {
                "label": label,
                "rows": bitmap_row_count(path),
                "mean_pixel": float(probe.mean()),
                "fraction_nonzero": float(np.mean(ink)),
                "border_ink_fraction": float(border.mean()),
                "center_ink_fraction": float(ink[:, 7:21, 7:21].mean()),
            }
        )
    stacked = np.concatenate(probes, axis=0)
    mean_pixel = float(stacked.mean())
    return {
        "seed": seed,
        "probe_rows_per_class": PROBE_ROWS,
        "mean_pixel": mean_pixel,
        "ink_polarity": decide_polarity(mean_pixel),
        "classes": classes,
        "histogram": {
            "bins": list(range(257)),
            "counts": np.bincount(stacked.reshape(-1), minlength=256).astype(int).tolist(),
        },
    }


def _sparsest(raw_dir: Path, per_class: int = 4) -> list[dict]:
    found = []
    for label in LABELS:
        path = bitmap_path(raw_dir, label)
        counts = _ink_counts(path)
        order = np.argsort(counts, kind="stable")
        for index in order[:per_class].tolist():
            stored = np.load(path, mmap_mode="r")
            found.append(
                {
                    "label": label,
                    "index": int(index),
                    "ink_pixels": int(counts[index]),
                    "image": np.asarray(stored[index]).reshape(28, 28),
                }
            )
    return found


def write_class_counts(report: dict, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    labels = [item["label"] for item in report["classes"]]
    counts = [item["rows"] for item in report["classes"]]
    figure, axis = plt.subplots(figsize=(7, 3.6))
    axis.bar(labels, counts, color="#7f9e7a")
    axis.set_ylabel("drawings in the numpy file")
    axis.set_title("Quick, Draw! class counts")
    figure.tight_layout()
    figure.savefig(destination, dpi=140)
    plt.close(figure)


def write_examples(raw_dir: Path, destination: Path, per_class: int = 16, seed: int = 1729) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(len(LABELS), per_class, figsize=(per_class * 0.85, len(LABELS) * 0.95))
    for row, label in enumerate(LABELS):
        probe = _load_probe(bitmap_path(raw_dir, label), per_class, seed)
        for column in range(per_class):
            axes[row, column].imshow(probe[column], cmap="gray", vmin=0, vmax=255)
            axes[row, column].set_xticks([])
            axes[row, column].set_yticks([])
            if column == 0:
                axes[row, column].set_ylabel(label, rotation=0, ha="right", va="center")
    figure.suptitle("Stored bitmaps, 16 drawings per class")
    figure.tight_layout()
    figure.savefig(destination, dpi=140)
    plt.close(figure)


def write_histogram(report: dict, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    counts = np.asarray(report["histogram"]["counts"], dtype=np.float64)
    figure, axis = plt.subplots(figsize=(7, 3.6))
    axis.bar(np.arange(256), counts, width=1.0, color="#5c6b7a")
    axis.set_xlabel("stored pixel value")
    axis.set_ylabel("count in the probe")
    axis.set_title("Pixel values across the six classes")
    figure.tight_layout()
    figure.savefig(destination, dpi=140)
    plt.close(figure)


def write_odd_samples(samples: list[dict], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    per_class = len(samples) // len(LABELS)
    figure, axes = plt.subplots(len(LABELS), per_class, figsize=(per_class * 1.5, len(LABELS) * 1.5))
    cursor = 0
    for row in range(len(LABELS)):
        for column in range(per_class):
            sample = samples[cursor]
            cursor += 1
            axes[row, column].imshow(sample["image"], cmap="gray", vmin=0, vmax=255)
            axes[row, column].set_xticks([])
            axes[row, column].set_yticks([])
            axes[row, column].set_title(f"{sample['label']} · {sample['ink_pixels']} px", fontsize=8)
    figure.suptitle("Sparsest drawings in each file")
    figure.tight_layout()
    figure.savefig(destination, dpi=140)
    plt.close(figure)


def _experiments_markdown(report: dict, odd: list[dict]) -> str:
    polarity = report["ink_polarity"]
    lines = [
        "# Experiments",
        "",
        "Numbers in this file come from `python -m doodleverse.data.explore` on the local bitmap files.",
        "",
        "## What a Quick, Draw! bitmap already is",
        "",
        "Each category file stores drawings as `uint8` rows of length 784. Reshaped, a row is a 28×28 image. "
        "Google already scaled the sketch into that square and centered the ink. The file is not a record of "
        "where the pen moved on a canvas, and it is not the same object as a stroke list typed into the app.",
        "",
        "The probe below is evidence from these files, not a second copy of Google's write-up. "
        "Ink is denser in the middle 14×14 pixels than in the outer two-pixel border, which is what a "
        "centered drawing looks like after it has been fit into the frame.",
        "",
        "## Polarity",
        "",
        f"Mean stored pixel across {report['probe_rows_per_class']} drawings per class: "
        f"{report['mean_pixel']:.2f} on a 0–255 scale. Seed {report['seed']}.",
        "",
        f"That mean is below mid-gray, so the decision is `{polarity}`."
        if polarity == "ink_high"
        else f"That mean is at or above mid-gray, so the decision is `{polarity}`.",
        "",
        "`ink_high` means the background is stored as 0 and the stroke is stored brighter. "
        "The training normalizer divides by 255 and does not invert. "
        "`ink_low` would divide by 255 and invert once. The rule is the mean compared with 127. "
        "A softmax model trained on one direction will misread a drawing stored the other way.",
        "",
        "| class | drawings in file | mean pixel | fraction nonzero | border ink | center ink |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in report["classes"]:
        lines.append(
            f"| {item['label']} | {item['rows']} | {item['mean_pixel']:.2f} | "
            f"{item['fraction_nonzero']:.3f} | {item['border_ink_fraction']:.3f} | "
            f"{item['center_ink_fraction']:.3f} |"
        )
    sparsest = ", ".join(f"{item['label']} {item['ink_pixels']} px" for item in odd[::4])
    lines.extend(
        [
            "",
            "## Figures",
            "",
            "- [Class counts](figures/class_counts.png)",
            "- [Sixteen examples per class](figures/examples.png), shown in stored polarity",
            "- [Pixel-value histogram](figures/pixel_histogram.png) of the same probe",
            "- [Sparsest drawings](figures/odd_samples.png). The emptiest row in each class has "
            f"{sparsest}.",
            "",
            "Those sparse rows are still labeled. A later model will treat a nearly blank cat and a "
            "finished cat as the same class. That is a property of the dataset, visible here before training.",
            "",
            "## Normalizer",
            "",
            "Training will call `normalize_quickdraw_bitmap`. A row is reshaped to 28×28, divided by 255 "
            f"when values still sit on the 0–255 scale, and left uninverted because the measured polarity is `{polarity}`. "
            "The result is float32 in [0, 1]. The same stored bitmap always produces the same tensor.",
            "",
            "This function does not redraw a stroke. A person drawing in the app produces points on a canvas "
            "of some width and height. Those points have not been centered in a 28×28 frame and have not been "
            "given Google's stroke thickness. If that live drawing is not mapped into this same numeric picture, "
            "the network is asked to recognize a kind of image it did not train on. That gap is train/serve skew, "
            "and it starts with the difference between these files and a raw canvas.",
            "",
        ]
    )
    return "\n".join(lines)


def explore(raw_dir: Path, figure_dir: Path, experiments_path: Path, seed: int = 1729) -> dict:
    report = measure(raw_dir, seed=seed)
    odd = _sparsest(raw_dir)
    report["sparsest"] = [
        {"label": item["label"], "index": item["index"], "ink_pixels": item["ink_pixels"]} for item in odd
    ]
    figure_dir.mkdir(parents=True, exist_ok=True)
    write_class_counts(report, figure_dir / "class_counts.png")
    write_examples(raw_dir, figure_dir / "examples.png", seed=seed)
    write_histogram(report, figure_dir / "pixel_histogram.png")
    write_odd_samples(odd, figure_dir / "odd_samples.png")
    experiments_path.parent.mkdir(parents=True, exist_ok=True)
    experiments_path.write_text(_experiments_markdown(report, odd), encoding="utf-8")
    summary = {key: value for key, value in report.items() if key != "histogram"}
    (figure_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return report


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Measure Quick, Draw! bitmaps and write the figures.")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--figure-dir", type=Path, default=Path("docs/figures"))
    parser.add_argument("--experiments", type=Path, default=Path("docs/experiments.md"))
    parser.add_argument("--seed", type=int, default=1729)
    args = parser.parse_args()
    report = explore(args.raw_dir, args.figure_dir, args.experiments, seed=args.seed)
    print(f"Polarity {report['ink_polarity']}, mean pixel {report['mean_pixel']:.2f}.")
    print(f"Wrote {args.experiments}")


if __name__ == "__main__":
    main()
