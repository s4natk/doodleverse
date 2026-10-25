from __future__ import annotations

import json
import warnings
from pathlib import Path

import joblib
import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import confusion_matrix

from doodleverse.classes import LABELS
from doodleverse.data.load import load_split
from doodleverse.data.splits import read_manifest
from doodleverse.models.baseline import aligned_proba, flatten_bitmaps, make_classifier
from doodleverse.tracking import log_run
from doodleverse.training.metrics import classification_scores
from doodleverse.training.plots import save_confusion

C_GRID = (0.01, 0.1, 1.0, 10.0)


def load_train_and_val(manifest: dict, raw_dir: Path, polarity: str = "ink_high"):
    """Train and validation only. The test split stays closed."""

    return (
        load_split(manifest, "train", raw_dir, polarity=polarity),
        load_split(manifest, "val", raw_dir, polarity=polarity),
    )


def _fit(c_value: float, features: np.ndarray, targets: np.ndarray, max_iter: int):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        model = make_classifier(c_value, max_iter=max_iter)
        model.fit(features, targets)
    converged = not any(issubclass(item.category, ConvergenceWarning) for item in caught)
    return model, converged


def run_baseline(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    out_dir: Path,
    max_iter: int = 2000,
    tracking_uri: Path | None = None,
) -> dict:
    """Fit one model per C on the full training split and keep the best validation macro-F1."""

    out_dir.mkdir(parents=True, exist_ok=True)
    flat_train = flatten_bitmaps(x_train)
    flat_val = flatten_bitmaps(x_val)
    trials = []
    best = None
    for c_value in C_GRID:
        model, converged = _fit(c_value, flat_train, y_train, max_iter)
        val_pred = model.predict(flat_val)
        scores = classification_scores(y_val, val_pred, LABELS)
        trials.append(
            {
                "C": c_value,
                "val_accuracy": scores["accuracy"],
                "val_macro_f1": scores["macro_f1"],
                "iterations": int(np.max(model.n_iter_)),
                "converged": converged,
            }
        )
        if best is None or scores["macro_f1"] > best["scores"]["macro_f1"]:
            best = {"model": model, "scores": scores, "C": c_value, "converged": converged, "val_pred": val_pred}

    model = best["model"]
    val_scores = best["scores"]
    train_scores = classification_scores(y_train, model.predict(flat_train), LABELS)
    matrix = confusion_matrix(y_val, best["val_pred"], labels=list(range(len(LABELS))))
    save_confusion(matrix, list(LABELS), out_dir / "confusion_val.png", "Logistic regression validation")
    joblib.dump({"model": model, "labels": list(LABELS), "C": best["C"]}, out_dir / "model.joblib")
    report = {
        "model": "logistic_regression",
        "solver": "lbfgs",
        "C": best["C"],
        "c_search": trials,
        "converged": best["converged"],
        "iterations": int(np.max(model.n_iter_)),
        "train_accuracy": train_scores["accuracy"],
        "train_macro_f1": train_scores["macro_f1"],
        "val_accuracy": val_scores["accuracy"],
        "val_macro_f1": val_scores["macro_f1"],
        "per_class": val_scores["per_class"],
        "confusion_matrix": matrix.tolist(),
        "parameter_count": int(np.size(model.coef_) + np.size(model.intercept_)),
        "labels": list(LABELS),
    }
    (out_dir / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    np.save(out_dir / "val_probabilities.npy", aligned_proba(model, flat_val, len(LABELS)))
    if tracking_uri is not None:
        log_run(
            tracking_uri,
            "doodleverse-baseline",
            "logistic-regression",
            {"C": best["C"], "solver": "lbfgs", "max_iter": max_iter},
            {
                "val_accuracy": report["val_accuracy"],
                "val_macro_f1": report["val_macro_f1"],
                "train_accuracy": report["train_accuracy"],
            },
            [out_dir / "confusion_val.png", out_dir / "metrics.json"],
        )
    return report


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Train logistic regression on the train split.")
    parser.add_argument("--manifest", type=Path, default=Path("ml/splits/v1.json"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/baseline"))
    parser.add_argument("--tracking-uri", type=Path, default=Path("mlruns"))
    args = parser.parse_args()
    manifest = read_manifest(args.manifest)
    (x_train, y_train), (x_val, y_val) = load_train_and_val(manifest, args.raw_dir)
    report = run_baseline(x_train, y_train, x_val, y_val, args.out_dir, tracking_uri=args.tracking_uri)
    print(
        f"C {report['C']}  val accuracy {report['val_accuracy']:.3f}  "
        f"macro-F1 {report['val_macro_f1']:.3f}  converged {report['converged']}"
    )


if __name__ == "__main__":
    main()
