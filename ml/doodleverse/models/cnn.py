from __future__ import annotations

import os

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import tensorflow as tf
from tensorflow import keras


def build_cnn(
    num_classes: int = 6,
    dropout: float = 0.3,
    bn_momentum: float = 0.9,
    interpolation: str = "nearest",
) -> keras.Model:
    """28×28 grayscale CNN. Translation noise is applied only while training."""

    inputs = keras.Input(shape=(28, 28, 1), name="bitmap")
    # Nearest keeps shifted strokes as sharp as the untranslated ones the
    # model sees at inference. Bilinear would blur every training image.
    features = keras.layers.RandomTranslation(
        height_factor=0.08,
        width_factor=0.08,
        fill_mode="constant",
        fill_value=0.0,
        interpolation=interpolation,
        name="shift",
    )(inputs)
    for index, filters in enumerate((32, 64, 128)):
        features = keras.layers.Conv2D(
            filters,
            kernel_size=3,
            padding="same",
            use_bias=False,
            name=f"conv_{index}",
        )(features)
        # Keras defaults to 0.99. With ~130 steps an epoch the inference statistics
        # lag the weights and validation accuracy swings between epochs.
        features = keras.layers.BatchNormalization(momentum=bn_momentum, name=f"bn_{index}")(features)
        features = keras.layers.ReLU(name=f"relu_{index}")(features)
        if index < 2:
            features = keras.layers.MaxPooling2D(name=f"pool_{index}")(features)
    features = keras.layers.GlobalAveragePooling2D(name="gap")(features)
    features = keras.layers.Dropout(dropout, name="dropout")(features)
    outputs = keras.layers.Dense(num_classes, activation="softmax", name="class_probs")(features)
    return keras.Model(inputs, outputs, name="doodle_cnn_gap")


def set_training_seed(seed: int) -> None:
    tf.keras.utils.set_random_seed(seed)
