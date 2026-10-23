import numpy as np
import pytest

from doodleverse.preprocess.bitmap import decide_polarity, normalize_quickdraw_bitmap


def test_same_bitmap_always_yields_the_same_tensor():
    raw = np.arange(784, dtype=np.uint8).reshape(28, 28)
    first = normalize_quickdraw_bitmap(raw, "ink_high")
    second = normalize_quickdraw_bitmap(raw, "ink_high")
    flat = normalize_quickdraw_bitmap(raw.reshape(784), "ink_high")
    np.testing.assert_array_equal(first, second)
    np.testing.assert_array_equal(first, flat)
    assert first.shape == (28, 28)
    assert first.dtype == np.float32
    assert float(first.min()) >= 0
    assert float(first.max()) <= 1


def test_known_pixels_scale_into_the_unit_interval():
    image = np.zeros((28, 28), dtype=np.uint8)
    image[0, 0] = 255
    image[0, 1] = 51
    scaled = normalize_quickdraw_bitmap(image, "ink_high")
    assert scaled[0, 0] == pytest.approx(1.0)
    assert scaled[0, 1] == pytest.approx(51 / 255)
    assert scaled[1, 1] == 0


def test_ink_low_inverts_once():
    paper = np.full((28, 28), 255, dtype=np.uint8)
    assert normalize_quickdraw_bitmap(paper, "ink_low")[0, 0] == pytest.approx(0.0)
    assert decide_polarity(40) == "ink_high"
    assert decide_polarity(200) == "ink_low"


def test_already_scaled_values_are_not_divided_again():
    scaled = np.full((28, 28), 0.5, dtype=np.float32)
    again = normalize_quickdraw_bitmap(scaled, "ink_high")
    np.testing.assert_array_equal(again, scaled)
