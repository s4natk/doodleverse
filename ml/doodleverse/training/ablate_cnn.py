"""Retrain the CNN with each training fix switched off to measure what it bought."""

from __future__ import annotations

import json
from pathlib import Path

from doodleverse.data.splits import read_manifest
from doodleverse.report import upsert_section
from doodleverse.training.train_baseline import load_train_and_val
from doodleverse.training.train_cnn import run_cnn

CONFIGS = (
    ("Keras defaults: momentum 0.99, bilinear shifts", 0.99, "bilinear"),
    ("Momentum 0.9, bilinear shifts", 0.9, "bilinear"),
    ("Momentum 0.9, nearest shifts (kept)", 0.9, "nearest"),
)


def _read(run_dir: Path) -> tuple[dict, dict]:
    report = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    history = json.loads((run_dir / "history.json").read_text(encoding="utf-8"))
    return report, history


def _matches(run_dir: Path, momentum: float, interpolation: str) -> bool:
    if not (run_dir / "metrics.json").exists():
        return False
    saved = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    return saved.get("bn_momentum") == momentum and saved.get("interpolation") == interpolation


def _stability(history: dict) -> tuple[float, float]:
    accuracy = history["val_accuracy"]
    drops = [earlier - later for earlier, later in zip(accuracy, accuracy[1:])]
    return accuracy[0], max([0.0, *drops])


def ablation_section(rows: list[dict]) -> str:
    defaults = rows[0]
    chance = 1 / 6
    start = (
        f"{defaults['first']:.3f}, chance for six classes,"
        if abs(defaults["first"] - chance) < 0.005
        else f"{defaults['first']:.3f} (chance is {chance:.3f})"
    )
    lines = [
        "## CNN training fixes",
        "",
        f"With Keras defaults, validation accuracy after the first epoch was {start} and fell by as much as "
        f"{defaults['drop']:.3f} between consecutive epochs, while training accuracy rose smoothly. Two "
        "settings were changed. Each is switched back below with the same split, seed, and schedule (up to "
        "20 epochs, early-stopping patience 4).",
        "",
        "Batch-norm momentum. Inference uses a moving average of each channel's mean and variance. At the "
        "default momentum of 0.99 that average spans roughly the last 100 steps, and after one 132-step epoch "
        "about a quarter of its weight still sits on the starting values. Momentum 0.9 spans roughly the last "
        "10 steps, so validation runs on statistics from the current weights.",
        "",
        "Shift interpolation. RandomTranslation moves each training image by a fractional number of pixels. "
        "Bilinear interpolation resamples, and so blurs, every training stroke. Validation images and live "
        "sketches are never shifted and stay sharp. Nearest interpolation shifts by whole pixels, so training "
        "and inference see strokes of the same sharpness.",
        "",
        "| configuration | epoch-1 val accuracy | largest epoch-to-epoch drop | best epoch "
        "| val accuracy | val macro-F1 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['name']} | {row['first']:.3f} | {row['drop']:.3f} | {row['best_epoch']} of "
            f"{row['epochs_ran']} | {row['val_accuracy']:.3f} | {row['val_macro_f1']:.3f} |"
        )
    if len(rows) == 3:
        momentum_gain = rows[1]["val_accuracy"] - rows[0]["val_accuracy"]
        shift_gain = rows[2]["val_accuracy"] - rows[1]["val_accuracy"]
        lines.extend(
            [
                "",
                f"Momentum moved validation accuracy by {momentum_gain:+.3f}. Nearest shifts moved it by "
                f"{shift_gain:+.3f} more. One seed on one split cannot separate a change that small from "
                "noise, so nearest is kept because it removes a train/inference mismatch, not for its score. "
                "Epoch-1 accuracy is a single noisy reading. The largest drop is the steadier measure of how "
                "much validation swings.",
            ]
        )
    return "\n".join(lines) + "\n"


def run_ablation(
    manifest_path: Path,
    raw_dir: Path,
    artifact_dir: Path,
    experiments_path: Path,
    tracking_uri: Path,
) -> list[dict]:
    manifest = read_manifest(manifest_path)
    (x_train, y_train), (x_val, y_val) = load_train_and_val(manifest, raw_dir)
    kept_run = artifact_dir / "cnn-gap"
    rows = []
    for index, (name, momentum, interpolation) in enumerate(CONFIGS):
        if _matches(kept_run, momentum, interpolation):
            report, history = _read(kept_run)
        else:
            run_dir = artifact_dir / "ablation" / f"config-{index}"
            run_cnn(
                x_train,
                y_train,
                x_val,
                y_val,
                run_dir,
                seed=manifest["seed"],
                bn_momentum=momentum,
                interpolation=interpolation,
                tracking_uri=tracking_uri,
                run_name=f"ablation-momentum{momentum}-{interpolation}",
            )
            report, history = _read(run_dir)
        first, drop = _stability(history)
        rows.append(
            {
                "name": name,
                "first": first,
                "drop": drop,
                "best_epoch": report["best_epoch"],
                "epochs_ran": report["epochs_ran"],
                "val_accuracy": report["val_accuracy"],
                "val_macro_f1": report["val_macro_f1"],
            }
        )
    upsert_section(experiments_path, "CNN training fixes", ablation_section(rows))
    summary = artifact_dir / "ablation" / "summary.json"
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return rows


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Measure the batch-norm and shift-interpolation fixes.")
    parser.add_argument("--manifest", type=Path, default=Path("ml/splits/v1.json"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--artifact-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--experiments", type=Path, default=Path("docs/experiments.md"))
    parser.add_argument("--tracking-uri", type=Path, default=Path("mlruns"))
    args = parser.parse_args()
    rows = run_ablation(args.manifest, args.raw_dir, args.artifact_dir, args.experiments, args.tracking_uri)
    for row in rows:
        print(f"{row['name']}: val accuracy {row['val_accuracy']:.3f}, largest drop {row['drop']:.3f}")


if __name__ == "__main__":
    main()
