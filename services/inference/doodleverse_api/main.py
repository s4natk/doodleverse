"""FastAPI app: GET /health, GET /model/info, POST /predict."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path

import anyio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from doodleverse_api.errors import error_response, install_handlers
from doodleverse_api.limits import BodySizeLimit
from doodleverse_api.predictor import Predictor
from doodleverse_api.schemas import Health, PredictRequest, PredictResponse
from doodleverse_api.settings import Settings

logger = logging.getLogger("doodleverse_api")


def _configure_logging() -> None:
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def create_app(settings: Settings | None = None, load: Callable[[Path], Predictor] = Predictor) -> FastAPI:
    settings = settings or Settings.from_env()
    _configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        started = time.perf_counter()
        app.state.predictor = load(settings.model_dir)
        app.state.limiter = anyio.CapacityLimiter(settings.max_concurrent_predictions)
        logger.info(
            "model loaded version=%s load_ms=%.0f",
            app.state.predictor.version,
            (time.perf_counter() - started) * 1000,
        )
        yield

    app = FastAPI(title="Doodleverse inference", version="0.1.0", lifespan=lifespan)
    # Added last so it wraps the size limit: a 413 still carries CORS headers the browser can read.
    app.add_middleware(BodySizeLimit, max_bytes=settings.max_body_bytes)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        max_age=600,
    )
    install_handlers(app)

    @app.get("/health", response_model=Health)
    def health(request: Request) -> Health:
        return Health(status="ok", model_version=request.app.state.predictor.version)

    @app.get("/model/info")
    def model_info(request: Request) -> dict:
        return request.app.state.predictor.info()

    @app.post("/predict", response_model=PredictResponse, responses={413: {}, 422: {}, 504: {}})
    async def predict(body: PredictRequest, request: Request) -> dict | JSONResponse:
        predictor = request.app.state.predictor
        strokes = [[tuple(point) for point in stroke] for stroke in body.strokes]
        points = sum(len(stroke) for stroke in strokes)
        started = time.perf_counter()
        try:
            with anyio.fail_after(settings.predict_timeout_s):
                result = await anyio.to_thread.run_sync(
                    partial(predictor.predict, strokes, body.canvas.width, body.canvas.height),
                    abandon_on_cancel=True,
                    limiter=request.app.state.limiter,
                )
        except TimeoutError:
            logger.warning(
                "predict timeout strokes=%d points=%d after_ms=%.0f",
                len(strokes),
                points,
                (time.perf_counter() - started) * 1000,
            )
            return error_response(504, "timeout")
        logger.info(
            "predict label=%s score=%.3f uncertain=%s strokes=%d points=%d latency_ms=%.1f",
            result["label"],
            result["score"],
            result["uncertain"],
            len(strokes),
            points,
            (time.perf_counter() - started) * 1000,
        )
        return result

    return app


app = create_app()
