import numpy as np

from doodleverse.classes import LABELS
from doodleverse.training.metrics import classification_scores


def test_scores_report_accuracy_macro_f1_and_per_class():
    y_true = np.array([0, 0, 1, 1])
    y_pred = np.array([0, 1, 1, 1])
    scores = classification_scores(y_true, y_pred, LABELS[:2])
    assert scores["accuracy"] == 0.75
    assert scores["per_class"][0]["label"] == "sun"
    assert scores["per_class"][0]["support"] == 2
    assert scores["per_class"][1]["recall"] == 1.0
    assert 0 < scores["macro_f1"] < 1
