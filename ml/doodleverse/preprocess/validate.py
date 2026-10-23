"""Reject sketches that are not a bounded list of finite points."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

MAX_STROKES = 64
MAX_POINTS = 4096
MAX_ABS_COORD = 1_000_000
MAX_CANVAS = 8192


class SketchValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SketchValidationError("invalid_point", "Point coordinates must be numbers.")
    number = float(value)
    if not math.isfinite(number):
        raise SketchValidationError("invalid_point", "Point coordinates must be finite.")
    if abs(number) > MAX_ABS_COORD:
        raise SketchValidationError(
            "coordinate_out_of_range",
            "A point is outside the accepted coordinate range.",
        )
    return number


def _as_point(point: object) -> tuple[float, float]:
    if isinstance(point, Mapping):
        if "x" not in point or "y" not in point:
            raise SketchValidationError("invalid_point", "Each point must include x and y.")
        return _number(point["x"]), _number(point["y"])
    if isinstance(point, Sequence) and not isinstance(point, (str, bytes)) and len(point) == 2:
        return _number(point[0]), _number(point[1])
    raise SketchValidationError("invalid_point", "Each point must be an (x, y) pair.")


def validate_sketch(
    strokes: object,
    canvas_width: int,
    canvas_height: int,
) -> list[list[tuple[float, float]]]:
    """Return cleaned strokes. An empty list is a blank drawing, not an error."""

    if isinstance(canvas_width, bool) or isinstance(canvas_height, bool):
        raise SketchValidationError("invalid_canvas", "Canvas size must be a positive integer.")
    if not isinstance(canvas_width, int) or not isinstance(canvas_height, int):
        raise SketchValidationError("invalid_canvas", "Canvas size must be a positive integer.")
    if canvas_width < 1 or canvas_height < 1 or canvas_width > MAX_CANVAS or canvas_height > MAX_CANVAS:
        raise SketchValidationError("invalid_canvas", "Canvas size is missing or too large.")
    if strokes is None or isinstance(strokes, (str, bytes)) or not isinstance(strokes, Sequence):
        raise SketchValidationError("invalid_strokes", "Strokes must be a list of polylines.")
    if len(strokes) > MAX_STROKES:
        raise SketchValidationError(
            "too_many_strokes",
            f"A sketch can contain at most {MAX_STROKES} strokes.",
        )

    cleaned: list[list[tuple[float, float]]] = []
    total_points = 0
    for stroke in strokes:
        if isinstance(stroke, (str, bytes)) or not isinstance(stroke, Sequence):
            raise SketchValidationError("invalid_strokes", "Each stroke must be a list of points.")
        if len(stroke) == 0:
            raise SketchValidationError("empty_stroke", "A stroke has no points.")
        points = [_as_point(point) for point in stroke]
        total_points += len(points)
        if total_points > MAX_POINTS:
            raise SketchValidationError(
                "too_many_points",
                f"A sketch can contain at most {MAX_POINTS} points.",
            )
        cleaned.append(points)
    return cleaned
