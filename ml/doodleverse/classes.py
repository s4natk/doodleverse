"""Softmax label order. Don't reorder this after training."""

from __future__ import annotations

LABELS: tuple[str, ...] = ("sun", "cloud", "tree", "flower", "car", "cat")
LABEL_TO_INDEX: dict[str, int] = {label: index for index, label in enumerate(LABELS)}
