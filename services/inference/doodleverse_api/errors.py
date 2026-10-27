"""Every error is `{"error": {"code", "message", "details"?}}`. Submitted points are never echoed back."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from doodleverse.preprocess.validate import MAX_ABS_COORD, MAX_CANVAS, MAX_POINTS, MAX_STROKES, SketchValidationError

logger = logging.getLogger("doodleverse_api")

MESSAGES = {
    "invalid_json": "The body is not valid JSON.",
    "invalid_request": "The body does not match the predict schema.",
    "invalid_canvas": f"canvas needs integer width and height from 1 to {MAX_CANVAS}.",
    "invalid_strokes": "strokes must be a list of strokes, each a list of [x, y] points.",
    "invalid_point": "Each point must be an [x, y] pair of finite numbers.",
    "coordinate_out_of_range": f"Coordinates must be within ±{MAX_ABS_COORD:,}.",
    "empty_sketch": "The sketch has no strokes.",
    "empty_stroke": "A stroke has no points.",
    "too_many_strokes": f"A sketch can contain at most {MAX_STROKES} strokes.",
    "too_many_points": f"A sketch can contain at most {MAX_POINTS} points.",
    "payload_too_large": "The body is too large.",
    "timeout": "Recognition took too long. Try again.",
    "not_found": "No such route.",
    "method_not_allowed": "That method is not allowed here.",
    "internal_error": "Something went wrong on the server.",
}
_RANGE = {"greater_than_equal", "less_than_equal"}


def error_response(status: int, code: str, message: str | None = None, details: list | None = None) -> JSONResponse:
    body: dict = {"code": code, "message": message or MESSAGES.get(code, code)}
    if details:
        body["details"] = details
    return JSONResponse(status_code=status, content={"error": body})


def validation_code(error: dict) -> str:
    """Map one pydantic error to the code `validate_sketch` would use for the same problem."""

    kind = error["type"]
    if kind == "json_invalid":
        return "invalid_json"
    if kind in MESSAGES:
        return kind
    loc = [part for part in error["loc"] if part != "body"]
    if not loc or loc[0] not in ("canvas", "strokes"):
        return "invalid_request"
    if loc[0] == "canvas":
        return "invalid_canvas"
    if len(loc) == 1:
        return {"too_long": "too_many_strokes", "too_short": "empty_sketch"}.get(kind, "invalid_strokes")
    if len(loc) == 2:
        return {"too_long": "too_many_points", "too_short": "empty_stroke"}.get(kind, "invalid_strokes")
    if len(loc) == 4 and kind in _RANGE:
        return "coordinate_out_of_range"
    return "invalid_point"


def validation_details(errors: list[dict], limit: int = 5) -> list[dict]:
    """Where and what, from pydantic's message. Its `input` field is dropped."""

    details = []
    for error in errors[:limit]:
        field = ".".join(str(part) for part in error["loc"] if part != "body") or "body"
        details.append({"field": field, "problem": error["msg"]})
    return details


def install_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _invalid(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = list(exc.errors())
        code = validation_code(errors[0]) if errors else "invalid_request"
        logger.info("rejected path=%s code=%s", request.url.path, code)
        return error_response(422, code, details=validation_details(errors))

    @app.exception_handler(SketchValidationError)
    async def _sketch(request: Request, exc: SketchValidationError) -> JSONResponse:
        logger.info("rejected path=%s code=%s", request.url.path, exc.code)
        return error_response(422, exc.code, str(exc))

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return error_response(exc.status_code, code, None if code != "http_error" else str(exc.detail))

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("failed path=%s", request.url.path)
        return error_response(500, "internal_error")
