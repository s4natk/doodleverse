import numpy as np
import pytest

from doodleverse.classes import LABELS
from doodleverse.data.load import load_split
from doodleverse.data.splits import make_manifest
from doodleverse.preprocess.bitmap import normalize_quickdraw_bitmap


def _write_bitmaps(directory, rows: int = 30) -> None:
    rng = np.random.default_rng(0)
    for label in LABELS:
        values = rng.integers(0, 256, size=(rows, 784), dtype=np.uint8)
        np.save(directory / f"{label}.npy", values)


def test_train_load_matches_the_bitmap_normalizer_and_skips_test_rows(tmp_path):
    _write_bitmaps(tmp_path)
    manifest = make_manifest({label: 30 for label in LABELS}, seed=4, samples_per_class=20)
    images, targets = load_split(manifest, "train", tmp_path, polarity="ink_high", allow_test=False)
    assert images.shape == (84, 28, 28)
    assert images.dtype == np.float32
    assert targets.dtype == np.int64
    assert float(images.min()) >= 0 and float(images.max()) <= 1
    assert np.bincount(targets, minlength=6).tolist() == [14] * 6

    stored = np.load(tmp_path / "sun.npy")
    train_sun = [row["index"] for row in manifest["splits"]["train"] if row["label"] == "sun"]
    test_sun = {row["index"] for row in manifest["splits"]["test"] if row["label"] == "sun"}
    assert test_sun.isdisjoint(train_sun)
    expected = normalize_quickdraw_bitmap(stored[train_sun[0]], "ink_high")
    first_sun = images[targets == 0][0]
    np.testing.assert_allclose(first_sun, expected, atol=1e-6)


def test_training_loader_refuses_the_test_split(tmp_path):
    _write_bitmaps(tmp_path, rows=20)
    manifest = make_manifest({label: 20 for label in LABELS}, seed=1, samples_per_class=10)
    with pytest.raises(RuntimeError, match="test split"):
        load_split(manifest, "test", tmp_path, allow_test=False)
