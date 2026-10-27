"""The accept rule behind the uncertainty gate. Threshold search and serving both use it."""

from __future__ import annotations

import numpy as np


def top_two(probs: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Predicted index, top-1 score, and top-1 minus top-2 for each row."""

    probs = np.asarray(probs, dtype=np.float64)
    ordered = np.sort(probs, axis=1)
    return probs.argmax(axis=1), ordered[:, -1], ordered[:, -1] - ordered[:, -2]


def accept(probs: np.ndarray, min_score: float, min_margin: float) -> np.ndarray:
    _, score, margin = top_two(probs)
    return (score >= min_score) & (margin >= min_margin)
