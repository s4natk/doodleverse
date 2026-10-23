from __future__ import annotations

from pathlib import Path

import numpy as np

from doodleverse.classes import LABEL_TO_INDEX, LABELS
from doodleverse.data.download import bitmap_path
from doodleverse.preprocess.bitmap import INPUT_SIZE

SPLIT_NAMES = ("train", "val", "test")


def load_split(
    manifest: dict,
    split: str,
    raw_dir: Path,
    polarity: str = "ink_high",
    allow_test: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Return float32 images `(N, 28, 28)` and int64 labels for one split.

    Only that split's row indices are read. Pass `allow_test=False` from
    training so the held-out rows cannot be opened by mistake.
    """

    if split not in SPLIT_NAMES:
        raise ValueError(f"Unknown split {split!r}.")
    if split == "test" and not allow_test:
        raise RuntimeError("Refusing to read the test split.")
    if polarity not in {"ink_high", "ink_low"}:
        raise ValueError("polarity must be 'ink_high' or 'ink_low'.")

    rows = manifest["splits"][split]
    grouped: dict[str, list[int]] = {label: [] for label in LABELS}
    positions: dict[str, list[int]] = {label: [] for label in LABELS}
    for position, row in enumerate(rows):
        label = str(row["label"])
        grouped[label].append(int(row["index"]))
        positions[label].append(position)

    images = np.empty((len(rows), INPUT_SIZE, INPUT_SIZE), dtype=np.float32)
    targets = np.empty((len(rows),), dtype=np.int64)
    for label in LABELS:
        indices = grouped[label]
        if not indices:
            continue
        stored = np.load(bitmap_path(raw_dir, label), mmap_mode="r")
        picked = np.asarray(stored[np.asarray(indices, dtype=np.int64)], dtype=np.float32)
        picked = picked.reshape(-1, INPUT_SIZE, INPUT_SIZE)
        if picked.size and float(picked.max()) > 1.0:
            picked /= np.float32(255.0)
        if polarity == "ink_low":
            picked = np.float32(1.0) - picked
        slots = np.asarray(positions[label], dtype=np.int64)
        images[slots] = picked
        targets[slots] = LABEL_TO_INDEX[label]
    return images, targets
