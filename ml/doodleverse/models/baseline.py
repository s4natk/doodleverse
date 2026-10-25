from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression


def flatten_bitmaps(images: np.ndarray) -> np.ndarray:
    array = np.asarray(images, dtype=np.float32)
    return array.reshape(array.shape[0], -1)


def make_classifier(c_value: float, max_iter: int = 2000) -> LogisticRegression:
    # lbfgs minimizes multinomial cross-entropy for multiclass targets and is
    # deterministic. C is the inverse L2 penalty.
    return LogisticRegression(C=c_value, solver="lbfgs", max_iter=max_iter, tol=1e-4)


def aligned_proba(model: LogisticRegression, features: np.ndarray, n_classes: int) -> np.ndarray:
    raw = model.predict_proba(features)
    aligned = np.zeros((features.shape[0], n_classes), dtype=np.float32)
    for column, label in enumerate(model.classes_):
        aligned[:, int(label)] = raw[:, column]
    return aligned
