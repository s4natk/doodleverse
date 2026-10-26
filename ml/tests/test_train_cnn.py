import numpy as np
from tensorflow import keras

from doodleverse.classes import LABELS
from doodleverse.training.train_cnn import run_cnn


def test_one_epoch_writes_a_reloadable_checkpoint_with_six_outputs(tmp_path):
    rng = np.random.default_rng(0)
    images = rng.random((24, 28, 28), dtype=np.float32)
    targets = np.tile(np.arange(len(LABELS)), 4)
    report = run_cnn(
        images[:18],
        targets[:18],
        images[18:],
        targets[18:],
        tmp_path / "run",
        epochs=1,
        batch_size=6,
        seed=1,
        tracking_uri=tmp_path / "mlflow",
    )
    assert report["epochs_ran"] == 1
    assert report["labels"] == list(LABELS)
    assert report["parameter_count"] > 1000
    assert report["filters"] == [32, 64, 128]
    restored = keras.models.load_model(tmp_path / "run" / "checkpoint.keras")
    assert restored(images[:3, ..., None], training=False).shape == (3, 6)

    narrow = run_cnn(
        images[:18],
        targets[:18],
        images[18:],
        targets[18:],
        tmp_path / "narrow",
        epochs=1,
        batch_size=6,
        seed=1,
        variant="narrow",
    )
    assert narrow["variant"] == "narrow"
    assert narrow["filters"] == [16, 32, 64]
    assert narrow["parameter_count"] < report["parameter_count"]
