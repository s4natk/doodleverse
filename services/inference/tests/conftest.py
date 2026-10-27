import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from doodleverse_api.main import create_app
from doodleverse_api.predictor import Predictor
from doodleverse_api.settings import Settings


@pytest.fixture(scope="session")
def model_dir(tmp_path_factory) -> Path:
    """An untrained CNN exported with a real sidecar. Enough to exercise the service, not to be right."""

    from doodleverse.models.cnn import build_cnn, set_training_seed
    from doodleverse.training.export import build_sidecar

    directory = tmp_path_factory.mktemp("model")
    set_training_seed(7)
    model = build_cnn()
    model.save(directory / "model.keras")
    report = {
        "variant": "gap",
        "filters": [32, 64, 128],
        "parameter_count": int(model.count_params()),
        "val_accuracy": 0.95,
        "val_macro_f1": 0.95,
    }
    gate = {"min_score": 0.0, "min_margin": 0.7, "target": 0.99, "val_coverage": 0.88, "val_accepted_accuracy": 0.99}
    manifest = {"seed": 1729, "samples_per_class": 4000}
    sidecar = build_sidecar(directory / "model.keras", report, gate, Path("ml/splits/v1.json"), manifest)
    (directory / "sidecar.json").write_text(json.dumps(sidecar), encoding="utf-8")
    return directory


@pytest.fixture(scope="session")
def predictor(model_dir) -> Predictor:
    return Predictor(model_dir)


@pytest.fixture
def make_client(model_dir, predictor):
    """A test client over the shared predictor. Keyword arguments override `Settings`."""

    def make(**overrides) -> TestClient:
        settings = Settings(model_dir=model_dir, **overrides)
        return TestClient(create_app(settings, load=lambda _: predictor))

    return make


@pytest.fixture
def client(make_client):
    with make_client() as test_client:
        yield test_client
