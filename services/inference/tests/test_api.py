import json
import logging
import math
import time
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from doodleverse.classes import LABELS
from doodleverse.preprocess.strokes import strokes_to_model_input
from doodleverse.preprocess.validate import MAX_CANVAS, MAX_POINTS, MAX_STROKES
from doodleverse_api.main import create_app
from doodleverse_api.predictor import ModelContractError, Predictor
from doodleverse_api.settings import Settings

REAL_MODEL = Path(__file__).resolve().parents[3] / "artifacts" / "model"


def _circle(cx: float, cy: float, radius: float, n: int = 32) -> list[list[float]]:
    return [
        [cx + radius * math.cos(2 * math.pi * i / n), cy + radius * math.sin(2 * math.pi * i / n)] for i in range(n + 1)
    ]


def _sun() -> list:
    strokes = [_circle(200, 200, 60)]
    for k in range(8):
        angle = 2 * math.pi * k / 8
        strokes.append(
            [
                [200 + 80 * math.cos(angle), 200 + 80 * math.sin(angle)],
                [200 + 125 * math.cos(angle), 200 + 125 * math.sin(angle)],
            ]
        )
    return strokes


SKETCH = {
    "canvas": {"width": 400, "height": 420},
    "strokes": [[[12.5, 18.25], [80, 24], [46, 96]], [[30, 40], [34, 70]]],
}


def test_health_names_the_loaded_model(client, predictor):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model_version": predictor.version}
    assert predictor.version.startswith("gap-")


def test_model_info_comes_from_the_sidecar(client, predictor):
    info = client.get("/model/info").json()
    assert info["labels"] == list(LABELS)
    assert info["gate"] == {"min_score": 0.0, "min_margin": 0.7, "target": 0.99}
    assert info["rasterizer"] == predictor.sidecar["rasterizer"]
    assert info["sha256"] == predictor.sidecar["sha256"]
    assert info["test"] is None


def test_predict_returns_label_score_top_three_version_and_flag(client, predictor):
    response = client.post("/predict", json=SKETCH)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"label", "score", "top3", "uncertain", "model_version", "latency_ms"}
    assert body["label"] in LABELS
    assert body["label"] == body["top3"][0]["label"]
    assert body["score"] == body["top3"][0]["score"]
    scores = [guess["score"] for guess in body["top3"]]
    assert len(scores) == 3 and scores == sorted(scores, reverse=True)
    assert all(0.0 <= score <= 1.0 for score in scores)
    assert len({guess["label"] for guess in body["top3"]}) == 3
    assert isinstance(body["uncertain"], bool)
    assert body["model_version"] == predictor.version
    assert body["latency_ms"] >= 0


def test_predict_matches_the_rasterizer_and_model_called_directly(client, predictor):
    expected_input = strokes_to_model_input(SKETCH["strokes"], 400, 420)
    np.testing.assert_array_equal(predictor.rasterize(SKETCH["strokes"], 400, 420), expected_input)
    probs = predictor.probabilities(expected_input)
    body = client.post("/predict", json=SKETCH).json()
    for guess in body["top3"]:
        assert guess["score"] == pytest.approx(float(probs[LABELS.index(guess["label"])]), abs=1e-6)
    assert body["label"] == LABELS[int(np.argmax(probs))]


def test_gate_from_the_sidecar_flags_close_calls(predictor, monkeypatch):
    monkeypatch.setattr(predictor, "probabilities", lambda tensor: np.array([0.55, 0.40, 0.02, 0.01, 0.01, 0.01]))
    assert predictor.predict(SKETCH["strokes"], 400, 420)["uncertain"] is True
    monkeypatch.setattr(predictor, "probabilities", lambda tensor: np.array([0.01, 0.95, 0.01, 0.01, 0.01, 0.01]))
    result = predictor.predict(SKETCH["strokes"], 400, 420)
    assert result["uncertain"] is False
    assert result["label"] == "cloud"


@pytest.mark.parametrize(
    ("body", "code"),
    [
        (b"{not json", "invalid_json"),
        (b"[1, 2]", "invalid_request"),
        (json.dumps({"strokes": SKETCH["strokes"]}).encode(), "invalid_canvas"),
        (json.dumps({"canvas": {"width": 400.5, "height": 420}, "strokes": [[[1, 1]]]}).encode(), "invalid_canvas"),
        (json.dumps({"canvas": SKETCH["canvas"], "strokes": "a sun"}).encode(), "invalid_strokes"),
        (json.dumps({"canvas": SKETCH["canvas"], "strokes": [[{"x": 1, "y": 2}]]}).encode(), "invalid_point"),
        (json.dumps({"canvas": SKETCH["canvas"], "strokes": [[[1, 2, 3]]]}).encode(), "invalid_point"),
        (json.dumps({"canvas": SKETCH["canvas"], "strokes": [[[True, 2]]]}).encode(), "invalid_point"),
        (b'{"canvas": {"width": 400, "height": 420}, "strokes": [[[NaN, 2]]]}', "invalid_point"),
        (json.dumps({**SKETCH, "label": "sun"}).encode(), "invalid_request"),
    ],
)
def test_malformed_bodies_get_a_structured_422(client, body, code):
    response = client.post("/predict", content=body, headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == code
    assert error["message"]


def test_empty_sketch_and_empty_stroke_are_refused(client):
    blank = client.post("/predict", json={"canvas": SKETCH["canvas"], "strokes": []})
    assert blank.status_code == 422 and blank.json()["error"]["code"] == "empty_sketch"
    hollow = client.post("/predict", json={"canvas": SKETCH["canvas"], "strokes": [[[1, 1]], []]})
    assert hollow.status_code == 422 and hollow.json()["error"]["code"] == "empty_stroke"
    assert hollow.json()["error"]["details"][0]["field"] == "strokes.1"


def test_limits_match_the_sketch_validator(client):
    def code(canvas: dict, strokes: list) -> str:
        response = client.post("/predict", json={"canvas": canvas, "strokes": strokes})
        assert response.status_code == 422
        return response.json()["error"]["code"]

    canvas = SKETCH["canvas"]
    assert code(canvas, [[[1, 1]]] * (MAX_STROKES + 1)) == "too_many_strokes"
    assert code(canvas, [[[1, 1]] * (MAX_POINTS // 2 + 1)] * 2) == "too_many_points"
    assert code(canvas, [[[1, 1]] * (MAX_POINTS + 1)]) == "too_many_points"
    assert code(canvas, [[[0, 0], [2e6, 1]]]) == "coordinate_out_of_range"
    assert code({"width": MAX_CANVAS + 1, "height": 10}, [[[1, 1]]]) == "invalid_canvas"
    assert code({"width": 0, "height": 10}, [[[1, 1]]]) == "invalid_canvas"
    longest = [[[index % 400, index % 7] for index in range(MAX_POINTS)]]
    assert client.post("/predict", json={"canvas": canvas, "strokes": longest}).status_code == 200


def test_oversize_bodies_are_refused_before_parsing(make_client):
    with make_client(max_body_bytes=2048) as client:
        big = {"canvas": SKETCH["canvas"], "strokes": [[[index, index] for index in range(400)]]}
        declared = client.post("/predict", json=big)
        assert declared.status_code == 413
        assert declared.json()["error"]["code"] == "payload_too_large"

        payload = json.dumps(big).encode()
        streamed = client.post(
            "/predict",
            content=(payload[start : start + 512] for start in range(0, len(payload), 512)),
            headers={"Content-Type": "application/json"},
        )
        assert streamed.status_code == 413
        assert client.post("/predict", json=SKETCH).status_code == 200


def test_cors_allows_the_web_origin_only(client):
    allowed = client.options(
        "/predict",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    refused = client.post("/predict", json=SKETCH, headers={"Origin": "https://elsewhere.example"})
    assert "access-control-allow-origin" not in refused.headers
    too_big = client.post(
        "/predict",
        content=b"x" * (300 * 1024),
        headers={"Origin": "http://localhost:3000", "Content-Type": "application/json"},
    )
    assert too_big.status_code == 413
    assert too_big.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_a_slow_prediction_times_out_with_504(make_client, predictor, monkeypatch):
    def stuck(*args, **kwargs):
        time.sleep(1.0)
        return {}

    monkeypatch.setattr(predictor, "predict", stuck)
    with make_client(predict_timeout_s=0.1) as client:
        started = time.perf_counter()
        response = client.post("/predict", json=SKETCH)
        elapsed = time.perf_counter() - started
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "timeout"
    assert elapsed < 0.9


def test_logs_carry_latency_and_label_but_never_points(client, caplog):
    caplog.set_level(logging.INFO, logger="doodleverse_api")
    marked = {"canvas": SKETCH["canvas"], "strokes": [[[123.4567, 98.7654], [222.2222, 11.1111]]]}
    client.post("/predict", json=marked)
    client.post(
        "/predict",
        content=b'{"canvas": {"width": 400, "height": 420}, "strokes": [[[123.4567, Infinity]]]}',
        headers={"Content-Type": "application/json"},
    )
    lines = [record.getMessage() for record in caplog.records if record.name == "doodleverse_api"]
    predict_line = next(line for line in lines if line.startswith("predict "))
    assert "label=" in predict_line and "latency_ms=" in predict_line
    assert any(line.startswith("rejected ") for line in lines)
    for value in ("123.4567", "98.7654", "222.2222", "11.1111"):
        assert value not in caplog.text


def test_unknown_routes_and_methods_are_structured(client):
    missing = client.get("/nope")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "not_found"
    wrong = client.get("/predict")
    assert wrong.status_code == 405 and wrong.json()["error"]["code"] == "method_not_allowed"


def test_a_sidecar_that_disagrees_with_the_code_stops_startup(tmp_path, model_dir):
    broken = tmp_path / "model"
    broken.mkdir()
    (broken / "model.keras").write_bytes((model_dir / "model.keras").read_bytes())
    sidecar = json.loads((model_dir / "sidecar.json").read_text(encoding="utf-8"))
    sidecar["labels"] = list(reversed(sidecar["labels"]))
    (broken / "sidecar.json").write_text(json.dumps(sidecar), encoding="utf-8")
    with pytest.raises(ModelContractError, match="labels"):
        with TestClient(create_app(Settings(model_dir=broken))):
            pass


@pytest.mark.skipif(not (REAL_MODEL / "sidecar.json").exists(), reason="no exported model in artifacts/model")
def test_the_exported_model_names_a_drawn_sun():
    with TestClient(create_app(Settings(model_dir=REAL_MODEL), load=Predictor)) as client:
        info = client.get("/model/info").json()
        response = client.post("/predict", json={"canvas": {"width": 400, "height": 400}, "strokes": _sun()})
    assert response.status_code == 200
    body = response.json()
    assert body["label"] == "sun"
    assert body["uncertain"] is False
    assert body["model_version"] == info["model_version"]
    assert info["test"]["count"] == 3600
