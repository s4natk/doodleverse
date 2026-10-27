"""Runtime settings, read from the environment once when the app is built."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

LOCAL_ORIGINS = ("http://localhost:3000", "http://127.0.0.1:3000")


@dataclass(frozen=True)
class Settings:
    model_dir: Path = Path("artifacts/model")
    cors_origins: tuple[str, ...] = LOCAL_ORIGINS
    # 4,096 points at full float precision come to about 170 KB of JSON.
    max_body_bytes: int = 256 * 1024
    predict_timeout_s: float = 2.0
    max_concurrent_predictions: int = 4

    @classmethod
    def from_env(cls) -> Settings:
        origins = os.environ.get("DOODLEVERSE_CORS_ORIGINS")
        return cls(
            model_dir=Path(os.environ.get("DOODLEVERSE_MODEL_DIR", str(cls.model_dir))),
            cors_origins=tuple(item.strip() for item in origins.split(",") if item.strip())
            if origins
            else LOCAL_ORIGINS,
            max_body_bytes=int(os.environ.get("DOODLEVERSE_MAX_BODY_BYTES", cls.max_body_bytes)),
            predict_timeout_s=float(os.environ.get("DOODLEVERSE_PREDICT_TIMEOUT_S", cls.predict_timeout_s)),
        )
