import json

import numpy as np
import pytest

from doodleverse.classes import LABELS
from doodleverse.data.splits import make_manifest, write_manifest


@pytest.fixture
def trained_run(tmp_path):
    """A one-step CNN saved the way training saves it, plus its report, gate, and a manifest."""

    from tensorflow import keras

    from doodleverse.models.cnn import build_cnn

    run = tmp_path / "cnn-gap"
    run.mkdir(parents=True)
    model = build_cnn()
    model.compile(optimizer=keras.optimizers.Adam(1e-3), loss="sparse_categorical_crossentropy")
    rng = np.random.default_rng(0)
    model.fit(rng.random((12, 28, 28, 1), dtype=np.float32), np.tile(np.arange(6), 2), epochs=1, verbose=0)
    model.save(run / "model.keras")
    report = {
        "variant": "gap",
        "filters": [32, 64, 128],
        "parameter_count": int(model.count_params()),
        "val_accuracy": 0.9,
        "val_macro_f1": 0.89,
        "model_bytes": (run / "model.keras").stat().st_size,
    }
    (run / "metrics.json").write_text(json.dumps(report), encoding="utf-8")
    gate = {
        "model_dir": run.as_posix(),
        "min_score": 0.0,
        "min_margin": 0.7,
        "target": 0.99,
        "val_coverage": 0.88,
        "val_accepted_accuracy": 0.99,
    }
    gate_path = tmp_path / "gate.json"
    gate_path.write_text(json.dumps(gate), encoding="utf-8")
    manifest_path = tmp_path / "splits" / "v1.json"
    write_manifest(make_manifest({label: 30 for label in LABELS}, seed=4, samples_per_class=20), manifest_path)
    return run, gate_path, manifest_path
