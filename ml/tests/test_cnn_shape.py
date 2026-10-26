import numpy as np

from doodleverse.models.cnn import CNN_VARIANTS, build_cnn


def test_cnn_probabilities_sum_to_one_and_are_stable():
    model = build_cnn()
    batch = np.random.default_rng(0).random((4, 28, 28, 1), dtype=np.float32)
    first = model(batch, training=False).numpy()
    second = model(batch, training=False).numpy()
    assert first.shape == (4, 6)
    np.testing.assert_allclose(first.sum(axis=1), np.ones(4), atol=1e-5)
    np.testing.assert_allclose(first, second, atol=1e-6)


def test_training_fixes_are_wired_into_the_layers():
    model = build_cnn()
    assert model.get_layer("shift").interpolation == "nearest"
    assert model.get_layer("bn_0").momentum == 0.9
    legacy = build_cnn(bn_momentum=0.99, interpolation="bilinear")
    assert legacy.get_layer("shift").interpolation == "bilinear"
    assert legacy.get_layer("bn_2").momentum == 0.99


def test_narrow_variant_halves_every_block():
    wide = build_cnn(filters=CNN_VARIANTS["gap"])
    narrow = build_cnn(filters=CNN_VARIANTS["narrow"])
    assert [narrow.get_layer(f"conv_{index}").filters for index in range(3)] == [16, 32, 64]
    assert narrow.count_params() < wide.count_params() / 3
    assert narrow.get_layer("bn_1").momentum == 0.9
    assert narrow(np.zeros((2, 28, 28, 1), dtype=np.float32), training=False).shape == (2, 6)
