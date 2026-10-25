import numpy as np

from doodleverse.classes import LABELS
from doodleverse.data.splits import make_manifest
from doodleverse.training.train_baseline import C_GRID, load_train_and_val, run_baseline


def _write_bitmaps(directory, rows: int) -> None:
    rng = np.random.default_rng(0)
    for index, label in enumerate(LABELS):
        values = rng.integers(0, 40, size=(rows, 784), dtype=np.uint8)
        values[:, index * 20 : index * 20 + 20] = 220
        np.save(directory / f"{label}.npy", values)


def test_baseline_searches_c_converges_and_is_repeatable(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    _write_bitmaps(raw, rows=24)
    manifest = make_manifest({label: 24 for label in LABELS}, seed=2, samples_per_class=12)
    (x_train, y_train), (x_val, y_val) = load_train_and_val(manifest, raw)
    assert len(x_train) == 48
    assert len(x_val) == 6
    first = run_baseline(x_train, y_train, x_val, y_val, tmp_path / "a", tracking_uri=tmp_path / "mlflow")
    second = run_baseline(x_train, y_train, x_val, y_val, tmp_path / "b")
    assert first["val_accuracy"] == second["val_accuracy"]
    assert first["val_macro_f1"] == second["val_macro_f1"]
    assert first["C"] == second["C"]
    assert [trial["C"] for trial in first["c_search"]] == list(C_GRID)
    assert first["converged"] is True
    assert (tmp_path / "a" / "model.joblib").exists()
    assert first["labels"] == list(LABELS)
