import json

import numpy as np
import pytest

from doodleverse.classes import LABELS
from doodleverse.preprocess.strokes import PAD_FRACTION, STROKE_WIDTH
from doodleverse.training.export import check_reload, export_model, sha256


def test_export_reloads_drops_optimizer_state_and_writes_the_sidecar(tmp_path, trained_run):
    run, gate_path, manifest_path = trained_run
    out = tmp_path / "model"
    sidecar = export_model(run, gate_path, manifest_path, out)

    probs = check_reload(out / "model.keras")
    assert probs.shape == (2, 6)
    np.testing.assert_allclose(probs.sum(axis=1), 1.0, atol=1e-5)
    assert (out / "model.keras").stat().st_size < (run / "model.keras").stat().st_size

    written = json.loads((out / "sidecar.json").read_text(encoding="utf-8"))
    assert written == sidecar
    assert sidecar["labels"] == list(LABELS)
    assert sidecar["input"]["size"] == 28
    assert sidecar["input"]["polarity"] == "ink_high"
    assert sidecar["input"]["range"] == [0.0, 1.0]
    assert sidecar["rasterizer"]["stroke_width"] == STROKE_WIDTH
    assert sidecar["rasterizer"]["pad_fraction"] == PAD_FRACTION
    assert sidecar["gate"] == {"min_score": 0.0, "min_margin": 0.7, "target": 0.99}
    assert sidecar["file_bytes"] == (out / "model.keras").stat().st_size
    assert sidecar["sha256"] == sha256(out / "model.keras")
    assert sidecar["test"] is None
    assert set(sidecar["git"]) == {"commit", "dirty"}


def test_gate_from_another_run_is_refused(tmp_path, trained_run):
    run, gate_path, manifest_path = trained_run
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    gate["model_dir"] = (tmp_path / "cnn-narrow").as_posix()
    gate_path.write_text(json.dumps(gate), encoding="utf-8")
    with pytest.raises(ValueError, match="chosen for"):
        export_model(run, gate_path, manifest_path, tmp_path / "model")


def test_a_test_scored_export_is_not_overwritten(tmp_path, trained_run):
    run, gate_path, manifest_path = trained_run
    out = tmp_path / "model"
    sidecar = export_model(run, gate_path, manifest_path, out)
    sidecar["test"] = {"accuracy": 0.9}
    (out / "sidecar.json").write_text(json.dumps(sidecar), encoding="utf-8")
    with pytest.raises(RuntimeError, match="test-scored export"):
        export_model(run, gate_path, manifest_path, out)
