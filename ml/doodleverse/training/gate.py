"""Accept a prediction only when its top score and its lead over the runner-up are both high enough.

The scores are softmax outputs, not calibrated probabilities. The thresholds are cut points on one
model's validation scores and have to be chosen again whenever the model is retrained.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from doodleverse.gate import accept, top_two

SCORE_GRID = (0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.98, 0.99)
MARGIN_GRID = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98)
TARGETS = (0.97, 0.98, 0.99, 0.995)
DEFAULT_TARGET = 0.99


def gate_stats(probs: np.ndarray, y_true: np.ndarray, min_score: float, min_margin: float) -> dict:
    predicted, _, _ = top_two(probs)
    kept = accept(probs, min_score, min_margin)
    right = predicted == np.asarray(y_true)
    accepted = int(kept.sum())
    return {
        "min_score": float(min_score),
        "min_margin": float(min_margin),
        "coverage": accepted / right.size if right.size else 0.0,
        "accepted_accuracy": float(right[kept].mean()) if accepted else float("nan"),
        "accepted": accepted,
        "errors_accepted": int((kept & ~right).sum()),
        "errors_total": int((~right).sum()),
    }


def choose_thresholds(
    probs: np.ndarray,
    y_true: np.ndarray,
    target: float = DEFAULT_TARGET,
    score_grid: tuple[float, ...] = SCORE_GRID,
    margin_grid: tuple[float, ...] = MARGIN_GRID,
) -> dict:
    """Widest coverage whose accepted accuracy reaches `target`. Ties keep the lower thresholds."""

    best = None
    for min_score in score_grid:
        for min_margin in margin_grid:
            stats = gate_stats(probs, y_true, min_score, min_margin)
            if stats["accepted"] == 0 or stats["accepted_accuracy"] < target:
                continue
            if best is None or stats["coverage"] > best["coverage"]:
                best = stats
    if best is None:
        raise ValueError(f"No threshold pair reaches an accepted accuracy of {target}.")
    return {**best, "target": target}


def calibration_error(probs: np.ndarray, y_true: np.ndarray, bins: int = 10) -> float:
    """Expected calibration error of the top-1 score over equal-width bins."""

    predicted, score, _ = top_two(probs)
    right = predicted == np.asarray(y_true)
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = 0.0
    for low, high in zip(edges[:-1], edges[1:]):
        inside = (score > low) & (score <= high)
        if inside.any():
            total += inside.mean() * abs(right[inside].mean() - score[inside].mean())
    return float(total)


def save_coverage_curve(probs: np.ndarray, y_true: np.ndarray, chosen: dict, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    sweep = np.linspace(0.0, 0.999, 400)
    figure, axis = plt.subplots(figsize=(6.4, 4.0))
    for name, pick in (("top-1 score only", lambda t: (t, 0.0)), ("margin only", lambda t: (0.0, t))):
        points = [gate_stats(probs, y_true, *pick(value)) for value in sweep]
        points = [point for point in points if point["accepted"]]
        axis.plot([p["coverage"] for p in points], [p["accepted_accuracy"] for p in points], label=name)
    axis.scatter([chosen["coverage"]], [chosen["accepted_accuracy"]], color="black", zorder=3, label="kept gate")
    axis.set_xlabel("coverage (share of drawings accepted)")
    axis.set_ylabel("accuracy on accepted drawings")
    axis.set_title("Validation coverage against accepted accuracy")
    axis.grid(alpha=0.3)
    axis.legend(loc="lower left")
    figure.tight_layout()
    figure.savefig(destination, dpi=120)
    plt.close(figure)
