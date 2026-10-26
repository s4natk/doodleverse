from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.metrics import confusion_matrix

from doodleverse.classes import LABELS
from doodleverse.data.splits import SEED
from doodleverse.models.cnn import CNN_VARIANTS, build_cnn, set_training_seed
from doodleverse.tracking import log_run
from doodleverse.training.metrics import classification_scores
from doodleverse.training.plots import save_confusion, save_learning_curves


def _channels(images: np.ndarray) -> np.ndarray:
    array = np.asarray(images, dtype=np.float32)
    if array.ndim == 3:
        array = array[..., None]
    return array


def run_cnn(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    out_dir: Path,
    epochs: int = 20,
    patience: int = 4,
    batch_size: int = 128,
    seed: int = SEED,
    bn_momentum: float = 0.9,
    interpolation: str = "nearest",
    tracking_uri: Path | None = None,
    run_name: str | None = None,
    variant: str = "gap",
) -> dict:
    """Fit one CNN variant. Early stopping restores the best validation-loss weights."""

    import tensorflow as tf
    from tensorflow import keras

    filters = CNN_VARIANTS[variant]
    out_dir.mkdir(parents=True, exist_ok=True)
    set_training_seed(seed)
    x_train = _channels(x_train)
    x_val = _channels(x_val)
    model = build_cnn(
        num_classes=len(LABELS),
        bn_momentum=bn_momentum,
        interpolation=interpolation,
        filters=filters,
    )
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-3),
        loss=keras.losses.SparseCategoricalCrossentropy(),
        metrics=[keras.metrics.SparseCategoricalAccuracy(name="accuracy")],
    )

    def dataset(features, targets, training: bool) -> tf.data.Dataset:
        pairs = tf.data.Dataset.from_tensor_slices((features, targets.astype(np.int64)))
        if training:
            pairs = pairs.shuffle(len(features), seed=seed, reshuffle_each_iteration=True)
        return pairs.batch(batch_size).prefetch(tf.data.AUTOTUNE)

    history = model.fit(
        dataset(x_train, y_train, True),
        validation_data=dataset(x_val, y_val, False),
        epochs=epochs,
        callbacks=[
            keras.callbacks.EarlyStopping(monitor="val_loss", patience=patience, restore_best_weights=True),
            keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=2, min_lr=1e-5),
            keras.callbacks.ModelCheckpoint(
                filepath=str(out_dir / "checkpoint.keras"),
                monitor="val_loss",
                save_best_only=True,
            ),
        ],
        verbose=2,
        shuffle=False,
    )
    history_dict = {key: [float(value) for value in values] for key, values in history.history.items()}
    best_epoch = int(np.argmin(history_dict["val_loss"]))
    model.save(out_dir / "model.keras")
    val_probs = model.predict(x_val, batch_size=256, verbose=0)
    val_pred = val_probs.argmax(axis=1)
    train_pred = model.predict(x_train, batch_size=256, verbose=0).argmax(axis=1)
    val_scores = classification_scores(y_val, val_pred, LABELS)
    train_scores = classification_scores(y_train, train_pred, LABELS)
    save_learning_curves(history_dict, out_dir / "learning_curves.png", "CNN")
    matrix = confusion_matrix(y_val, val_pred, labels=list(range(len(LABELS))))
    save_confusion(matrix, list(LABELS), out_dir / "confusion_val.png", "CNN validation")
    report = {
        "model": "tensorflow_cnn",
        "variant": variant,
        "filters": list(filters),
        "seed": seed,
        "epochs_ran": len(history_dict["loss"]),
        "best_epoch": best_epoch + 1,
        "optimizer": "adam",
        "learning_rate": 1e-3,
        "loss": "sparse_categorical_crossentropy",
        "bn_momentum": bn_momentum,
        "interpolation": interpolation,
        "augmentation": "random_translation_0.08_train_only",
        "train_loss": history_dict["loss"][best_epoch],
        "val_loss": history_dict["val_loss"][best_epoch],
        "train_accuracy": train_scores["accuracy"],
        "val_accuracy": val_scores["accuracy"],
        "train_macro_f1": train_scores["macro_f1"],
        "val_macro_f1": val_scores["macro_f1"],
        "per_class": val_scores["per_class"],
        "confusion_matrix": matrix.tolist(),
        "parameter_count": int(model.count_params()),
        "model_bytes": (out_dir / "model.keras").stat().st_size,
        "labels": list(LABELS),
    }
    (out_dir / "history.json").write_text(json.dumps(history_dict), encoding="utf-8")
    (out_dir / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    np.save(out_dir / "val_probabilities.npy", val_probs)
    if tracking_uri is not None:
        log_run(
            tracking_uri,
            "doodleverse-cnn",
            run_name or f"cnn-{variant}",
            {
                "variant": variant,
                "filters": "/".join(str(width) for width in filters),
                "seed": seed,
                "epochs_ran": report["epochs_ran"],
                "best_epoch": report["best_epoch"],
                "bn_momentum": bn_momentum,
                "interpolation": interpolation,
            },
            {
                "val_accuracy": report["val_accuracy"],
                "val_macro_f1": report["val_macro_f1"],
                "val_loss": report["val_loss"],
                "train_accuracy": report["train_accuracy"],
                "parameter_count": report["parameter_count"],
            },
            [out_dir / "learning_curves.png", out_dir / "confusion_val.png", out_dir / "metrics.json"],
        )
    return report
