import numpy as np
import pytest

from doodleverse.gate import accept, top_two
from doodleverse.training.analyze import errors_section, gate_section
from doodleverse.training.gate import calibration_error, choose_thresholds, gate_stats

PROBS = np.array(
    [
        [0.98, 0.01, 0.01],
        [0.90, 0.05, 0.05],
        [0.55, 0.40, 0.05],
        [0.50, 0.45, 0.05],
        [0.10, 0.85, 0.05],
        [0.40, 0.35, 0.25],
    ]
)
Y_TRUE = np.array([0, 0, 1, 0, 1, 2])


def test_top_two_returns_the_score_and_the_lead_over_the_runner_up():
    predicted, score, margin = top_two(PROBS)
    assert predicted.tolist() == [0, 0, 0, 0, 1, 0]
    np.testing.assert_allclose(score[:3], [0.98, 0.90, 0.55])
    np.testing.assert_allclose(margin[:3], [0.97, 0.85, 0.15])


def test_both_thresholds_have_to_clear():
    assert accept(PROBS, 0.5, 0.0).tolist() == [True, True, True, True, True, False]
    assert accept(PROBS, 0.5, 0.2).tolist() == [True, True, False, False, True, False]


def test_stats_count_coverage_and_mistakes_let_through():
    stats = gate_stats(PROBS, Y_TRUE, 0.5, 0.0)
    assert stats["accepted"] == 5
    assert stats["errors_accepted"] == 1
    assert stats["errors_total"] == 2
    assert stats["accepted_accuracy"] == pytest.approx(0.8)


def test_chosen_gate_reaches_the_target_with_the_widest_coverage():
    chosen = choose_thresholds(PROBS, Y_TRUE, target=1.0, score_grid=(0.0, 0.5, 0.9), margin_grid=(0.0, 0.2))
    assert chosen["accepted_accuracy"] == 1.0
    assert chosen["coverage"] == pytest.approx(3 / 6)
    assert (chosen["min_score"], chosen["min_margin"]) == (0.0, 0.2)
    with pytest.raises(ValueError):
        choose_thresholds(np.array([[0.6, 0.4]]), np.array([1]), target=0.99)


def test_calibration_error_is_zero_when_scores_match_accuracy():
    probs = np.array([[0.75, 0.25]] * 4)
    assert calibration_error(probs, np.array([0, 0, 0, 1])) == pytest.approx(0.0)
    assert calibration_error(probs, np.array([1, 1, 1, 1])) == pytest.approx(0.75)


def test_sections_are_written_from_the_measured_numbers():
    rows = [choose_thresholds(PROBS, Y_TRUE, 1.0)]
    section = gate_section(rows, rows[0], accuracy=0.667, mean_score=0.62, ece=0.05)
    assert section.startswith("## Uncertainty gate")
    assert "not calibrated probabilities" in section
    assert "0.050" in section

    pairs = [
        {"true": "tree", "predicted": "flower", "count": 3, "share": 0.3, "ink": 0.97, "held_back": 2},
    ]
    summary = {
        "mistakes": 3,
        "total": 10,
        "median_score_right": 0.99,
        "median_score_wrong": 0.7,
        "wrong_below_0_9": 0.67,
        "right_below_0_9": 0.1,
    }
    sink = {"label": "flower", "count": 3, "inkiest": False, "ink": 1.2}
    errors = errors_section("The gap CNN", pairs, summary, sink)
    assert "| tree | flower | 3 | 30.0% | 0.97× | 2 of 3 |" in errors
    assert "lollipop" in errors
    assert "carry the most ink" not in errors
