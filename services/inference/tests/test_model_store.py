import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from doodleverse_api.main import create_app
from doodleverse_api.model_store import fetch_model, parse_s3_uri
from doodleverse_api.predictor import Predictor
from doodleverse_api.settings import Settings

URI = "s3://models-bucket/models/gap-test"


class FolderAsBucket:
    """Answers `download_file` from a local folder laid out the way the bucket is."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.keys: list[str] = []

    def download_file(self, bucket: str, key: str, filename: str) -> None:
        self.keys.append(key)
        shutil.copyfile(self.root / bucket / key, filename)


@pytest.fixture
def bucket(tmp_path, model_dir) -> FolderAsBucket:
    prefix = tmp_path / "s3" / "models-bucket" / "models" / "gap-test"
    prefix.mkdir(parents=True)
    for name in ("sidecar.json", "model.keras"):
        shutil.copyfile(model_dir / name, prefix / name)
    return FolderAsBucket(tmp_path / "s3")


def test_s3_uris_name_a_bucket_and_a_prefix():
    assert parse_s3_uri("s3://models-bucket/models/gap-test/") == ("models-bucket", "models/gap-test")
    for bad in ("models-bucket/models", "s3://models-bucket", "s3:///models", "https://example.com/models"):
        with pytest.raises(ValueError):
            parse_s3_uri(bad)


def test_fetch_copies_the_sidecar_then_the_model_it_names(bucket, tmp_path):
    destination = fetch_model(URI, tmp_path / "model", client=bucket)
    assert bucket.keys == ["models/gap-test/sidecar.json", "models/gap-test/model.keras"]
    assert Predictor(destination).version.startswith("gap-")


def test_a_sidecar_cannot_name_a_file_outside_the_copy(bucket, tmp_path):
    sidecar = bucket.root / "models-bucket" / "models" / "gap-test" / "sidecar.json"
    contents = json.loads(sidecar.read_text(encoding="utf-8"))
    sidecar.write_text(json.dumps({**contents, "model_file": "../model.keras"}), encoding="utf-8")
    with pytest.raises(ValueError, match="plain file name"):
        fetch_model(URI, tmp_path / "model", client=bucket)


def test_the_service_starts_from_s3_when_a_model_uri_is_set(bucket, tmp_path):
    settings = Settings(model_dir=tmp_path / "cache", model_uri=URI)
    app = create_app(settings, fetch=lambda uri, destination: fetch_model(uri, destination, client=bucket))
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"
    assert (tmp_path / "cache" / "model.keras").exists()


def test_the_model_uri_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("DOODLEVERSE_MODEL_URI", URI)
    assert Settings.from_env().model_uri == URI
    monkeypatch.setenv("DOODLEVERSE_MODEL_URI", "")
    assert Settings.from_env().model_uri is None
