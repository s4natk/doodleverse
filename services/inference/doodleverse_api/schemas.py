"""Request and response bodies. The limits are the ones `doodleverse.preprocess.validate` enforces."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError

from doodleverse.preprocess.validate import MAX_ABS_COORD, MAX_CANVAS, MAX_POINTS, MAX_STROKES

Coordinate = Annotated[float, Field(strict=True, allow_inf_nan=False, ge=-MAX_ABS_COORD, le=MAX_ABS_COORD)]
Point = tuple[Coordinate, Coordinate]
Stroke = Annotated[list[Point], Field(min_length=1, max_length=MAX_POINTS)]
Side = Annotated[int, Field(strict=True, ge=1, le=MAX_CANVAS)]


class Canvas(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: Side
    height: Side


class PredictRequest(BaseModel):
    """One sketch: strokes of `[x, y]` points in canvas pixels, and the canvas they were drawn on."""

    model_config = ConfigDict(extra="forbid")

    canvas: Canvas
    strokes: Annotated[list[Stroke], Field(min_length=1, max_length=MAX_STROKES)]

    @model_validator(mode="after")
    def _total_points(self) -> PredictRequest:
        if sum(len(stroke) for stroke in self.strokes) > MAX_POINTS:
            raise PydanticCustomError(
                "too_many_points",
                "A sketch can contain at most {limit} points.",
                {"limit": MAX_POINTS},
            )
        return self


class Guess(BaseModel):
    label: str
    score: float


class PredictResponse(BaseModel):
    label: str
    score: float
    top3: list[Guess]
    uncertain: bool
    model_version: str
    latency_ms: float


class Health(BaseModel):
    status: str
    model_version: str
