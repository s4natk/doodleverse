"""Where a classifier is wrong: confused pairs, score spread, and a gallery of the mistakes."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def confused_pairs(matrix: np.ndarray, labels: list[str] | tuple[str, ...], top: int = 6) -> list[dict]:
    """Off-diagonal cells, largest first. `share` is the fraction of that true class."""

    matrix = np.asarray(matrix)
    support = matrix.sum(axis=1)
    cells = []
    for true in range(matrix.shape[0]):
        for predicted in range(matrix.shape[1]):
            count = int(matrix[true, predicted])
            if true == predicted or count == 0:
                continue
            cells.append(
                {
                    "true": labels[true],
                    "predicted": labels[predicted],
                    "true_index": true,
                    "predicted_index": predicted,
                    "count": count,
                    "share": count / max(int(support[true]), 1),
                }
            )
    cells.sort(key=lambda cell: (-cell["count"], cell["true_index"], cell["predicted_index"]))
    return cells[:top]


def false_positives(matrix: np.ndarray) -> np.ndarray:
    """Per predicted class, how many drawings of other classes landed there."""

    matrix = np.asarray(matrix)
    return matrix.sum(axis=0) - np.diag(matrix)


def score_summary(y_true: np.ndarray, probs: np.ndarray) -> dict:
    top = probs.max(axis=1)
    right = probs.argmax(axis=1) == np.asarray(y_true)
    return {
        "total": int(right.size),
        "mistakes": int((~right).sum()),
        "median_score_right": float(np.median(top[right])) if right.any() else float("nan"),
        "median_score_wrong": float(np.median(top[~right])) if (~right).any() else float("nan"),
        "right_below_0_9": float(np.mean(top[right] < 0.9)) if right.any() else 0.0,
        "wrong_below_0_9": float(np.mean(top[~right] < 0.9)) if (~right).any() else 0.0,
    }


def mean_ink(images: np.ndarray) -> np.ndarray:
    return np.asarray(images, dtype=np.float32).reshape(len(images), -1).mean(axis=1)


def class_ink(ink: np.ndarray, y_true: np.ndarray, predicted: np.ndarray, n_classes: int) -> np.ndarray:
    """Mean ink of the correctly classified drawings in each class."""

    right = predicted == y_true
    return np.array([ink[right & (y_true == label)].mean() for label in range(n_classes)])


def ink_ratio(ink: np.ndarray, typical: np.ndarray, y_true: np.ndarray, rows: np.ndarray) -> float:
    """Ink of `rows` relative to correct drawings of their own true class. 1.0 is typical."""

    if len(rows) == 0:
        return float("nan")
    return float(np.mean(ink[rows] / typical[np.asarray(y_true)[rows]]))


def pair_rows(y_true: np.ndarray, predicted: np.ndarray, true_index: int, predicted_index: int) -> np.ndarray:
    return np.flatnonzero((np.asarray(y_true) == true_index) & (predicted == predicted_index))


def pair_examples(
    y_true: np.ndarray,
    probs: np.ndarray,
    true_index: int,
    predicted_index: int,
    limit: int,
) -> np.ndarray:
    """Rows with this mistake, most confident first."""

    rows = pair_rows(y_true, probs.argmax(axis=1), true_index, predicted_index)
    order = np.argsort(-probs[rows, predicted_index], kind="stable")
    return rows[order][:limit]


def save_mistake_gallery(
    images: np.ndarray,
    y_true: np.ndarray,
    probs: np.ndarray,
    pairs: list[dict],
    destination: Path,
    per_row: int = 10,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(
        len(pairs),
        per_row,
        figsize=(per_row * 0.95, len(pairs) * 1.25),
        squeeze=False,
    )
    for row, pair in enumerate(pairs):
        picked = pair_examples(y_true, probs, pair["true_index"], pair["predicted_index"], per_row)
        for column in range(per_row):
            axis = axes[row, column]
            axis.set_xticks([])
            axis.set_yticks([])
            if column < len(picked):
                index = picked[column]
                axis.imshow(np.asarray(images[index]).reshape(28, 28), cmap="gray", vmin=0, vmax=1)
                axis.set_title(f"{probs[index, pair['predicted_index']]:.2f}", fontsize=7)
            else:
                axis.axis("off")
            if column == 0:
                axis.set_ylabel(
                    f"{pair['true']} → {pair['predicted']}\n({pair['count']})",
                    rotation=0,
                    ha="right",
                    va="center",
                    fontsize=8,
                )
    figure.suptitle("Validation mistakes, most confident first (score of the wrong class)", fontsize=9)
    figure.tight_layout()
    figure.savefig(destination, dpi=140)
    plt.close(figure)
