"""Turn a Quick, Draw! bitmap into the float tensor training will see.

Google's files are already 28×28. This function does not center, pad, or
redraw them. It only sets the numeric range: float32 values in [0, 1], with
ink near 1 and paper near 0. A live canvas stroke is a different picture and
is not handled here.
"""

from __future__ import annotations

import numpy as np

INPUT_SIZE = 28


def decide_polarity(mean_pixel: float) -> str:
    """Choose ink direction from the mean of stored pixel values on a 0–255 scale.

    A page that is mostly empty is dark when the background is 0, so the mean
    sits well below mid-gray. That case is ink_high: bright strokes, no invert.
    A mean at or above mid-gray is ink_low: the file stores paper as bright,
    and the normalizer inverts once after scaling.
    """

    if not np.isfinite(mean_pixel) or mean_pixel < 0 or mean_pixel > 255:
        raise ValueError("mean_pixel must be a finite value from 0 through 255.")
    if mean_pixel < 127:
        return "ink_high"
    return "ink_low"


def normalize_quickdraw_bitmap(image: np.ndarray, polarity: str = "ink_high") -> np.ndarray:
    """Return float32 `(28, 28)` in `[0, 1]`.

    Apply this once. `ink_low` inverts after scaling, so a second call would
    flip the drawing back. An array whose maximum is already at most 1 is
    treated as scaled and is not divided by 255 again.
    """

    if polarity not in {"ink_high", "ink_low"}:
        raise ValueError("polarity must be 'ink_high' or 'ink_low'.")
    array = np.asarray(image)
    if array.ndim == 1:
        if array.size != INPUT_SIZE * INPUT_SIZE:
            raise ValueError(
                f"Flat bitmap has {array.size} values; expected {INPUT_SIZE * INPUT_SIZE}."
            )
        array = array.reshape(INPUT_SIZE, INPUT_SIZE)
    if array.shape != (INPUT_SIZE, INPUT_SIZE):
        raise ValueError(f"Bitmap shape {array.shape} is not {(INPUT_SIZE, INPUT_SIZE)}.")
    values = array.astype(np.float32, copy=False)
    peak = float(values.max()) if values.size else 0.0
    if peak > 1.0:
        values = values / np.float32(255.0)
    if polarity == "ink_low":
        values = np.float32(1.0) - values
    return np.ascontiguousarray(values, dtype=np.float32)
