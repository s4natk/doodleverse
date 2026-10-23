"""Scale an already-28×28 Quick, Draw! bitmap to float32 in [0, 1]."""

from __future__ import annotations

import numpy as np

INPUT_SIZE = 28


def decide_polarity(mean_pixel: float) -> str:
    """Mean under 127 is ink_high (0 is paper). Otherwise invert once."""

    if not np.isfinite(mean_pixel) or mean_pixel < 0 or mean_pixel > 255:
        raise ValueError("mean_pixel must be a finite value from 0 through 255.")
    if mean_pixel < 127:
        return "ink_high"
    return "ink_low"


def normalize_quickdraw_bitmap(image: np.ndarray, polarity: str = "ink_high") -> np.ndarray:
    """float32 (28, 28) in [0, 1]. Call once; ink_low inverts."""

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
