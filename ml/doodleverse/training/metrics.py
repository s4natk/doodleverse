from __future__ import annotations

import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support


def classification_scores(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    labels: list[str] | tuple[str, ...],
) -> dict:
    """Accuracy, macro-F1, and per-class precision/recall. No probability calibration."""

    precision, recall, f1, support = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=list(range(len(labels))),
        zero_division=0,
    )
    per_class = []
    for index, label in enumerate(labels):
        per_class.append(
            {
                "label": label,
                "precision": float(precision[index]),
                "recall": float(recall[index]),
                "f1": float(f1[index]),
                "support": int(support[index]),
            }
        )
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "per_class": per_class,
    }
