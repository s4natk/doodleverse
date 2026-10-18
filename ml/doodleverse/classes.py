"""Fixed order of the six sketch classes.

Index 0 is the first output unit of the classifier later days will train.
Reordering this tuple after that training would rename every prediction
without changing a weight.
"""

from __future__ import annotations

LABELS: tuple[str, ...] = ("sun", "cloud", "tree", "flower", "car", "cat")
LABEL_TO_INDEX: dict[str, int] = {label: index for index, label in enumerate(LABELS)}
