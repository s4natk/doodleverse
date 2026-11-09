import pytest

from doodleverse.classes import LABELS
from doodleverse.training.model_card import model_card, top_confusions


@pytest.fixture
def inputs():
    matrix = [[100 if true == predicted else 0 for predicted in range(6)] for true in range(6)]
    matrix[2][3] = 9
    matrix[5][4] = 4
    matrix[0][5] = 1
    per_class = [
        {"label": label, "precision": 0.9, "recall": 0.9 - 0.01 * index, "f1": 0.9, "support": 100}
        for index, label in enumerate(LABELS)
    ]
    sidecar = {
        "variant": "gap",
        "sha256": "1ce366c1a170" + "0" * 52,
        "file_bytes": 433944,
        "filters": [32, 64, 128],
        "parameter_count": 94118,
        "tensorflow": "2.21.0",
        "keras": "3.15.1",
        "git": {"commit": "a31d5736400a", "dirty": True},
        "input": {"size": 28, "polarity": "ink_high"},
        "rasterizer": {"raster_size": 256, "stroke_width": 12, "pad_fraction": 0.08},
        "gate": {"min_score": 0.0, "min_margin": 0.7, "target": 0.99},
        "validation": {"accuracy": 0.952, "macro_f1": 0.951, "gate_coverage": 0.882, "gate_accepted_accuracy": 0.991},
        "test": {
            "count": 600,
            "accuracy": 0.95,
            "macro_f1": 0.949,
            "gate_coverage": 0.868,
            "gate_accepted_accuracy": 0.9914,
            "per_class": per_class,
            "confusion_matrix": matrix,
        },
    }
    gate = {"val_mean_score": 0.94, "val_calibration_error": 0.0167}
    skew = {
        "per_class": 1000,
        "bitmaps_check": {"accuracy": 0.9487},
        "before": {"stroke_width": 18, "pad_fraction": 0.12, "check": {"accuracy": 0.9163}},
        "chosen": {"stroke_width": 12, "pad_fraction": 0.08, "check": {"accuracy": 0.9467}},
    }
    comparison = {"baseline": {"val_macro_f1": 0.831, "C": 0.1}}
    manifest = {
        "seed": 1729,
        "samples_per_class": 4000,
        "splits": {"train": [0] * 16800, "val": [0] * 3600, "test": [0] * 3600},
    }
    return sidecar, gate, skew, comparison, manifest


def test_confusions_are_the_largest_off_diagonal_cells(inputs):
    matrix = inputs[0]["test"]["confusion_matrix"]
    assert top_confusions(matrix, 2) == [("tree", "flower", 9), ("cat", "car", 4)]


def test_the_card_carries_the_numbers_it_was_given(inputs):
    card = model_card(*inputs)
    for expected in (
        "`gap-1ce366c1a170`",
        "94,118 parameters, 424 KB",
        "| test | 600 | 0.950 | 0.949 | 86.8% | 0.991 |",
        "16,800 for training",
        "seed 1729",
        "tree → flower (9)",
        "Weakest class: cat",
        "0.831 validation macro-F1",
        "calibration error over ten bins was 0.017",
        "| our raster, width 12, pad 0.08 (shipped) | 0.947 |",
        "commit `a31d573` with uncommitted changes",
    ):
        assert expected in card, expected
    assert "None" not in card


def test_there_is_no_card_before_the_test_split_is_scored(inputs):
    sidecar, *rest = inputs
    with pytest.raises(ValueError, match="no test score"):
        model_card({**sidecar, "test": None}, *rest)
