import numpy as np
import pytest

from doodleverse.training.errors import (
    class_ink,
    confused_pairs,
    false_positives,
    ink_ratio,
    mean_ink,
    pair_examples,
    save_mistake_gallery,
    score_summary,
)

LABELS = ("sun", "cloud", "tree")
MATRIX = np.array([[8, 1, 1], [0, 9, 1], [0, 4, 6]])


def test_pairs_are_largest_first_with_the_share_of_the_true_class():
    pairs = confused_pairs(MATRIX, LABELS, top=3)
    assert [(pair["true"], pair["predicted"], pair["count"]) for pair in pairs] == [
        ("tree", "cloud", 4),
        ("sun", "cloud", 1),
        ("sun", "tree", 1),
    ]
    assert pairs[0]["share"] == 0.4
    assert all(pair["true"] != pair["predicted"] for pair in confused_pairs(MATRIX, LABELS, top=10))


def test_false_positives_count_other_classes_per_column():
    assert false_positives(MATRIX).tolist() == [0, 5, 2]


def test_examples_are_the_mistakes_of_one_pair_most_confident_first():
    y_true = np.array([2, 2, 2, 0])
    probs = np.array(
        [
            [0.1, 0.6, 0.3],
            [0.0, 0.9, 0.1],
            [0.1, 0.1, 0.8],
            [0.1, 0.8, 0.1],
        ]
    )
    assert pair_examples(y_true, probs, 2, 1, limit=5).tolist() == [1, 0]
    assert pair_examples(y_true, probs, 2, 1, limit=1).tolist() == [1]


def test_score_summary_splits_right_from_wrong():
    y_true = np.array([0, 0, 1])
    probs = np.array([[0.95, 0.05], [0.4, 0.6], [0.2, 0.8]])
    summary = score_summary(y_true, probs)
    assert summary["mistakes"] == 1
    assert summary["wrong_below_0_9"] == 1.0
    assert summary["right_below_0_9"] == 0.5


def test_ink_ratio_is_relative_to_correct_drawings_of_the_same_class():
    images = np.zeros((4, 28, 28), dtype=np.float32)
    images[0, :2] = 1
    images[1, :2] = 1
    images[2, :4] = 1
    y_true = np.array([0, 0, 0, 1])
    predicted = np.array([0, 0, 1, 1])
    ink = mean_ink(images)
    typical = class_ink(ink, y_true, predicted, 2)
    assert ink_ratio(ink, typical, y_true, np.array([2])) == pytest.approx(2.0)
    assert np.isnan(ink_ratio(ink, typical, y_true, np.array([], dtype=int)))


def test_gallery_writes_a_figure(tmp_path):
    rng = np.random.default_rng(0)
    images = rng.random((12, 28, 28), dtype=np.float32)
    y_true = np.array([2] * 6 + [0] * 6)
    probs = np.tile([0.1, 0.7, 0.2], (12, 1))
    pairs = confused_pairs(np.array([[0, 6, 0], [0, 0, 0], [0, 6, 0]]), LABELS, top=2)
    destination = tmp_path / "mistakes.png"
    save_mistake_gallery(images, y_true, probs, pairs, destination, per_row=8)
    assert destination.stat().st_size > 0
