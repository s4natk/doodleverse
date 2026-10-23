"""Class-balanced 70/15/15 splits. Each drawing index is used once."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from doodleverse.classes import LABELS

SEED = 1729
SAMPLES_PER_CLASS = 4000
TRAIN_FRACTION = 0.70
VAL_FRACTION = 0.15
SPLIT_NAMES = ("train", "val", "test")


def make_manifest(
    class_counts: dict[str, int],
    seed: int = SEED,
    samples_per_class: int = SAMPLES_PER_CLASS,
) -> dict:
    """Same seed and class counts always return the same indices."""

    missing = [label for label in LABELS if label not in class_counts]
    if missing:
        raise ValueError(f"Missing class counts for {missing}.")
    if samples_per_class < 10:
        raise ValueError("samples_per_class must be at least 10 so every split is non-empty.")

    rng = np.random.default_rng(seed)
    n_train = int(samples_per_class * TRAIN_FRACTION)
    n_val = int(samples_per_class * VAL_FRACTION)
    n_test = samples_per_class - n_train - n_val
    if n_train < 1 or n_val < 1 or n_test < 1:
        raise ValueError("Split fractions produced an empty split.")

    splits: dict[str, list[dict[str, int | str]]] = {name: [] for name in SPLIT_NAMES}
    for label in LABELS:
        count = int(class_counts[label])
        if count < samples_per_class:
            raise ValueError(
                f"{label} has {count} drawings, which is fewer than {samples_per_class}."
            )
        chosen = rng.choice(count, size=samples_per_class, replace=False)
        rng.shuffle(chosen)
        grouped = {
            "train": chosen[:n_train],
            "val": chosen[n_train : n_train + n_val],
            "test": chosen[n_train + n_val :],
        }
        for split_name, indices in grouped.items():
            for index in indices.tolist():
                splits[split_name].append({"label": label, "index": int(index)})

    return {
        "seed": int(seed),
        "samples_per_class": int(samples_per_class),
        "labels": list(LABELS),
        "fractions": {
            "train": n_train / samples_per_class,
            "val": n_val / samples_per_class,
            "test": n_test / samples_per_class,
        },
        "splits": splits,
    }


def assert_manifest_integrity(manifest: dict) -> dict[str, dict[str, int]]:
    """Raise if any (label, index) pair is reused or a class is unbalanced."""

    seen: set[tuple[str, int]] = set()
    counts: dict[str, dict[str, int]] = {
        split: {label: 0 for label in LABELS} for split in SPLIT_NAMES
    }
    if list(manifest["labels"]) != list(LABELS):
        raise AssertionError("Manifest label order does not match the model contract.")
    if set(manifest["splits"]) != set(SPLIT_NAMES):
        raise AssertionError("Manifest is missing a split.")
    for split_name in SPLIT_NAMES:
        for row in manifest["splits"][split_name]:
            key = (str(row["label"]), int(row["index"]))
            if key in seen:
                raise AssertionError(f"Duplicate example {key} leaked across splits.")
            seen.add(key)
            if key[0] not in counts[split_name]:
                raise AssertionError(f"Unexpected label {key[0]}.")
            counts[split_name][key[0]] += 1
    for split_name, by_label in counts.items():
        totals = set(by_label.values())
        if len(totals) != 1 or 0 in totals:
            raise AssertionError(f"{split_name} is not class-balanced: {by_label}")
    return counts


def write_manifest(manifest: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest), encoding="utf-8")


def read_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert_manifest_integrity(manifest)
    return manifest
