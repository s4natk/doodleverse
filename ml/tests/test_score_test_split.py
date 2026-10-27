import json

import numpy as np
import pytest

from doodleverse.classes import LABELS
from doodleverse.training.export import export_model
from doodleverse.training.score_test_split import guard_path, score_test_once


@pytest.fixture
def exported(tmp_path, trained_run):
    run, gate_path, manifest_path = trained_run
    raw = tmp_path / "raw"
    raw.mkdir()
    rng = np.random.default_rng(1)
    for label in LABELS:
        np.save(raw / f"{label}.npy", rng.integers(0, 256, size=(30, 784), dtype=np.uint8))
    out = tmp_path / "model"
    export_model(run, gate_path, manifest_path, out)
    return manifest_path, raw, out


def test_test_split_is_scored_once_and_recorded(tmp_path, exported):
    manifest_path, raw, out = exported
    experiments = tmp_path / "experiments.md"
    experiments.write_text("# Experiments\n\n## Export\n\nfrozen\n", encoding="utf-8")
    test = score_test_once(manifest_path, raw, out, experiments, tmp_path / "figures")

    assert test["count"] == 18
    assert 0.0 <= test["accuracy"] <= 1.0
    sidecar = json.loads((out / "sidecar.json").read_text(encoding="utf-8"))
    assert sidecar["test"]["accuracy"] == test["accuracy"]
    record = json.loads(guard_path(manifest_path).read_text(encoding="utf-8"))
    assert record["model_sha256"] == sidecar["sha256"]
    assert record["count"] == 18
    assert "## Test split" in experiments.read_text(encoding="utf-8")
    assert (tmp_path / "figures" / "test_confusion.png").exists()

    with pytest.raises(RuntimeError, match="already scored"):
        score_test_once(manifest_path, raw, out, experiments, tmp_path / "figures")


def test_a_model_that_does_not_match_its_sidecar_is_not_scored(tmp_path, exported):
    manifest_path, raw, out = exported
    with (out / "model.keras").open("ab") as handle:
        handle.write(b"tampered")
    with pytest.raises(RuntimeError, match="SHA-256"):
        score_test_once(manifest_path, raw, out, tmp_path / "experiments.md", tmp_path / "figures")
    assert not guard_path(manifest_path).exists()
