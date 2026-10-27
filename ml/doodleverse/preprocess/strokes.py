"""Rasterize one sketch to float32 (1, 28, 28, 1), ink high.

One scale for both axes, then pad and center. Thickness is fixed before
INTER_AREA down to 28. Google's bitmaps did not come from this function.
"""

from __future__ import annotations

import cv2
import numpy as np

from doodleverse.preprocess.bitmap import INPUT_SIZE, normalize_quickdraw_bitmap
from doodleverse.preprocess.validate import validate_sketch

RASTER_SIZE = 256
# Both are tuned so rasters match the Quick, Draw! bitmaps. Changing either needs a
# rerun of `doodleverse.training.skew` and a new golden fixture.
PAD_FRACTION = 0.08
# 12 px on the 256 canvas is about 1.3 px after the area resize to 28.
STROKE_WIDTH = 12


def _frame(points: list[tuple[float, float]], pad_fraction: float) -> tuple[float, float, float]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    # The floor keeps a single dot from dividing by zero. Centering on the
    # true midpoint keeps that dot in the middle instead of the top-left.
    side = max(max_x - min_x, max_y - min_y, 1e-3)
    padded = side * (1 + 2 * pad_fraction)
    offset_x = (min_x + max_x) / 2 - padded / 2
    offset_y = (min_y + max_y) / 2 - padded / 2
    return offset_x, offset_y, padded


def _to_pixel(x: float, y: float, offset_x: float, offset_y: float, padded: float) -> tuple[int, int]:
    scale = (RASTER_SIZE - 1) / padded
    return int(round((x - offset_x) * scale)), int(round((y - offset_y) * scale))


def _draw(strokes: list[list[tuple[float, float]]], stroke_width: int, pad_fraction: float) -> np.ndarray:
    flat = [point for stroke in strokes for point in stroke]
    offset_x, offset_y, padded = _frame(flat, pad_fraction)
    image = np.zeros((RASTER_SIZE, RASTER_SIZE), dtype=np.uint8)
    radius = stroke_width // 2
    for stroke in strokes:
        pixels = [_to_pixel(x, y, offset_x, offset_y, padded) for x, y in stroke]
        if len(pixels) >= 2:
            cv2.polylines(
                image,
                [np.asarray(pixels, dtype=np.int32)],
                isClosed=False,
                color=255,
                thickness=stroke_width,
                lineType=cv2.LINE_8,
            )
        for x, y in pixels:
            cv2.circle(image, (x, y), radius, 255, thickness=-1, lineType=cv2.LINE_8)
    return image


def strokes_to_raster(
    strokes: object,
    canvas_width: int,
    canvas_height: int,
    stroke_width: int = STROKE_WIDTH,
    pad_fraction: float = PAD_FRACTION,
) -> np.ndarray:
    """Return float32 `(28, 28)` in `[0, 1]`, ink high, paper low.

    `stroke_width` and `pad_fraction` exist for the skew probe. Serving uses the defaults.
    """

    cleaned = validate_sketch(strokes, canvas_width, canvas_height)
    if not cleaned:
        return np.zeros((INPUT_SIZE, INPUT_SIZE), dtype=np.float32)
    drawn = _draw(cleaned, stroke_width, pad_fraction)
    small = cv2.resize(drawn, (INPUT_SIZE, INPUT_SIZE), interpolation=cv2.INTER_AREA)
    return normalize_quickdraw_bitmap(small, polarity="ink_high")


def strokes_to_model_input(
    strokes: object,
    canvas_width: int,
    canvas_height: int,
    stroke_width: int = STROKE_WIDTH,
    pad_fraction: float = PAD_FRACTION,
) -> np.ndarray:
    """Return float32 `(1, 28, 28, 1)`, the rank a convolutional model consumes."""

    image = strokes_to_raster(strokes, canvas_width, canvas_height, stroke_width, pad_fraction)
    return image.reshape(1, INPUT_SIZE, INPUT_SIZE, 1)
