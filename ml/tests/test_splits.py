import json

import pytest

from doodleverse.classes import LABELS
from doodleverse.data.splits import assert_manifest_integrity, make_manifest


def _counts(rows: int = 100) -> dict[str, int]:
    return {label: rows for label in LABELS}


def test_splits_are_balanced_reproducible_and_disjoint():
    first = make_manifest(_counts(), seed=1729, samples_per_class=40)
    second = make_manifest(_counts(), seed=1729, samples_per_class=40)
    assert first == second
    counts = assert_manifest_integrity(first)
    assert counts["train"]["sun"] == 28
    assert counts["val"]["cat"] == 6
    assert counts["test"]["tree"] == 6
    assert counts["train"]["sun"] == counts["train"]["flower"]


def test_different_seed_changes_indices():
    left = make_manifest(_counts(), seed=1, samples_per_class=40)
    right = make_manifest(_counts(), seed=2, samples_per_class=40)
    assert left["splits"]["train"] != right["splits"]["train"]


def test_too_few_drawings_are_rejected():
    with pytest.raises(ValueError):
        make_manifest(_counts(10), seed=1, samples_per_class=40)


def test_leaking_manifest_is_rejected():
    manifest = make_manifest(_counts(), seed=3, samples_per_class=40)
    leaked = json.loads(json.dumps(manifest))
    leaked["splits"]["test"].append(dict(leaked["splits"]["train"][0]))
    with pytest.raises(AssertionError, match="leaked"):
        assert_manifest_integrity(leaked)
