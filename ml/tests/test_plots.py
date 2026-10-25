import numpy as np

from doodleverse.training.plots import save_confusion, save_learning_curves


def test_confusion_and_learning_curve_files(tmp_path):
    matrix = np.array([[3, 1], [0, 2]])
    confusion_path = tmp_path / "confusion.png"
    save_confusion(matrix, ["sun", "cloud"], confusion_path, "toy")
    assert confusion_path.stat().st_size > 0

    history = {
        "loss": [1.0, 0.5],
        "val_loss": [1.1, 0.6],
        "accuracy": [0.4, 0.7],
        "val_accuracy": [0.3, 0.6],
    }
    curve_path = tmp_path / "curves.png"
    save_learning_curves(history, curve_path, "toy")
    assert curve_path.stat().st_size > 0
