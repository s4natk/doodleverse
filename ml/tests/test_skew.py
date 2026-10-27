import numpy as np

from doodleverse.training.skew import (
    BEFORE,
    PADS,
    WIDTHS,
    agreement,
    manifest_indices,
    pick,
    roll_within_class,
    skew_section,
)


def test_agreement_reports_correlation_and_ink_ratio():
    rng = np.random.default_rng(0)
    bitmaps = rng.random((5, 28, 28), dtype=np.float32)
    same = agreement(bitmaps, bitmaps)
    assert same["correlation"] > 0.999
    assert same["ink_ratio"] == 1.0
    assert agreement(bitmaps * 2, bitmaps)["ink_ratio"] == 2.0


def test_roll_pairs_each_drawing_with_another_of_its_class():
    images = np.arange(5).reshape(5, 1, 1)
    y = np.array([0, 0, 0, 1, 1])
    assert roll_within_class(images, y).ravel().tolist() == [2, 0, 1, 4, 3]


def test_every_split_is_skipped_for_that_class():
    manifest = {
        "splits": {
            "train": [{"label": "sun", "index": 4}, {"label": "cat", "index": 9}],
            "val": [{"label": "sun", "index": 7}],
            "test": [{"label": "sun", "index": 1}],
        }
    }
    assert manifest_indices(manifest, "sun") == {1, 4, 7}


def _result(width: int, pad: float, tune: float, loss: float = 0.3, check: float = 0.9) -> dict:
    scores = {"accuracy": tune, "macro_f1": tune, "log_loss": loss, "mean_score": 0.9, "coverage": 0.8}
    return {
        "stroke_width": width,
        "pad_fraction": pad,
        "all": {**scores, "accepted_accuracy": 0.98},
        "tune": scores,
        "check": {**scores, "accuracy": check},
        "correlation": 0.95,
        "ink_ratio": 1.1,
    }


def test_pick_uses_tune_accuracy_then_log_loss():
    rows = [_result(12, 0.08, 0.94, loss=0.30), _result(14, 0.08, 0.94, loss=0.25), _result(18, 0.12, 0.91)]
    assert (pick(rows)["stroke_width"], pick(rows)["pad_fraction"]) == (14, 0.08)


def test_section_reports_before_after_and_the_shipped_settings():
    before = _result(*BEFORE, tune=0.91, check=0.915)
    chosen = _result(12, 0.08, tune=0.943, check=0.947)
    grid = [chosen if (width, pad) == (12, 0.08) else _result(width, pad, 0.9) for width in WIDTHS for pad in PADS]
    grid = [before if (row["stroke_width"], row["pad_fraction"]) == BEFORE else row for row in grid]
    bitmaps = {"accuracy": 0.946, "macro_f1": 0.946, "mean_score": 0.94, "coverage": 0.88, "accepted_accuracy": 0.99}
    summary = {
        "per_class": 1000,
        "lines_read": 6186,
        "skipped": 186,
        "rejected": 0,
        "alignment": {"same": 0.93, "other": 0.3},
        "validation_accuracy": 0.952,
        "validation_macro_f1": 0.952,
        "gate": {"val_mean_score": 0.94, "val_coverage": 0.882, "val_accepted_accuracy": 0.991},
        "bitmaps": bitmaps,
        "bitmaps_check": {**bitmaps, "accuracy": 0.949},
        "before": before,
        "chosen": chosen,
        "shipped": chosen,
        "grid": grid,
    }
    section = skew_section(summary)
    assert section.startswith("## Stroke skew")
    assert "6,186 lines read, 186 skipped" in section
    assert "| sample, our raster, width 12, pad 0.08 |" in section
    assert "accuracy went from 0.915 to 0.947, against 0.949" in section
    assert "now ship as width 12, pad 0.08" in section
