"""Where the frozen model comes from: a local directory, or an S3 prefix copied down once at startup."""

from __future__ import annotations

import json
from pathlib import Path

from doodleverse_api.predictor import SIDECAR_FILE


def parse_s3_uri(uri: str) -> tuple[str, str]:
    """`s3://bucket/models/gap-1ce366c1a170` as (bucket, prefix)."""

    bucket, _, prefix = uri.removeprefix("s3://").partition("/")
    if not uri.startswith("s3://") or not bucket or not prefix.strip("/"):
        raise ValueError(f"Expected s3://bucket/prefix, got {uri!r}.")
    return bucket, prefix.strip("/")


def fetch_model(uri: str, destination: Path, client=None) -> Path:
    """Copy the sidecar, then the model file it names, from the S3 prefix `uri` into `destination`.

    The Predictor checks the model file against the sidecar's SHA-256, so a swapped or partial copy stops startup.
    """

    bucket, prefix = parse_s3_uri(uri)
    if client is None:
        import boto3

        client = boto3.client("s3")
    destination.mkdir(parents=True, exist_ok=True)
    sidecar_path = destination / SIDECAR_FILE
    client.download_file(bucket, f"{prefix}/{SIDECAR_FILE}", str(sidecar_path))
    model_file = json.loads(sidecar_path.read_text(encoding="utf-8"))["model_file"]
    if Path(model_file).name != model_file:
        raise ValueError(f"The sidecar names {model_file!r} as its model, which is not a plain file name.")
    client.download_file(bucket, f"{prefix}/{model_file}", str(destination / model_file))
    return destination
