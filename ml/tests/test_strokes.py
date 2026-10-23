from pathlib import Path

import numpy as np
import pytest

from doodleverse.preprocess.strokes import strokes_to_model_input, strokes_to_raster
from doodleverse.preprocess.validate import SketchValidationError

FIXTURE = Path(__file__).parent / "fixtures" / "golden_stroke.npy"
GOLDEN_STROKES = [
    [{"x": 12.0, "y": 18.0}, {"x": 80.0, "y": 24.0}, {"x": 46.0, "y": 96.0}],
    [(30.0, 40.0), (34.0, 70.0)],
]


def test_empty_sketch_is_blank():
    image = strokes_to_raster([], 200, 120)
    assert image.shape == (28, 28)
    assert image.dtype == np.float32
    assert image.sum() == 0


def test_single_point_and_tiny_drawing_leave_ink():
    point = strokes_to_raster([[(40, 40)]], 100, 100)
    tiny = strokes_to_raster([[(10, 10), (10.01, 10.02)]], 100, 100)
    assert point.sum() > 0
    assert tiny.sum() > 0
    assert point.max() <= 1


def test_disconnected_strokes_occupy_opposite_corners():
    image = strokes_to_raster(
        [[(0, 0), (0, 12)], [(80, 80), (92, 80)]],
        120,
        120,
    )
    assert image[:14, :14].sum() > 0
    assert image[14:, 14:].sum() > 0


def test_canvas_size_does_not_change_the_framed_ink():
    strokes = [[(10, 10), (70, 16), (40, 80)]]
    left = strokes_to_raster(strokes, 200, 200)
    right = strokes_to_raster(strokes, 900, 500)
    np.testing.assert_array_equal(left, right)


def test_raster_is_deterministic():
    strokes = [[(5, 5), (40, 20), (20, 60)], [(30, 30), (32, 48)]]
    np.testing.assert_array_equal(
        strokes_to_raster(strokes, 300, 180),
        strokes_to_raster(strokes, 300, 180),
    )


def test_model_input_rank():
    tensor = strokes_to_model_input([[(1, 1), (20, 8)]], 64, 64)
    assert tensor.shape == (1, 28, 28, 1)
    assert tensor.dtype == np.float32


def test_out_of_range_long_blank_and_invalid_payloads():
    with pytest.raises(SketchValidationError) as out_of_range:
        strokes_to_raster([[(0, 0), (1e12, 1)]], 100, 100)
    assert out_of_range.value.code == "coordinate_out_of_range"

    with pytest.raises(SketchValidationError) as too_long:
        strokes_to_raster([[(index, 0) for index in range(5000)]], 800, 200)
    assert too_long.value.code == "too_many_points"

    with pytest.raises(SketchValidationError) as blank:
        strokes_to_raster(None, 100, 100)
    assert blank.value.code == "invalid_strokes"

    with pytest.raises(SketchValidationError):
        strokes_to_raster("nope", 100, 100)
    with pytest.raises(SketchValidationError):
        strokes_to_raster([[{"z": 1}]], 100, 100)
    with pytest.raises(SketchValidationError):
        strokes_to_raster([[(float("nan"), 1)]], 100, 100)
    with pytest.raises(SketchValidationError):
        strokes_to_raster([[]], 100, 100)
    with pytest.raises(SketchValidationError):
        strokes_to_raster([[(1, 2)]], 0, 100)


def test_golden_stroke_matches_the_locked_fixture():
    image = strokes_to_raster(GOLDEN_STROKES, 240, 180)
    expected = np.load(FIXTURE)
    np.testing.assert_allclose(image, expected, atol=1e-5)
