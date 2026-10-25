import numpy as np

from doodleverse.models.baseline import aligned_proba, flatten_bitmaps, make_classifier


def test_flatten_keeps_every_pixel():
    images = np.arange(2 * 28 * 28, dtype=np.float32).reshape(2, 28, 28)
    flat = flatten_bitmaps(images)
    assert flat.shape == (2, 784)
    assert flat[1, 0] == images[1, 0, 0]


def test_classifier_proba_columns_follow_class_ids():
    rng = np.random.default_rng(0)
    features = rng.normal(size=(36, 8)).astype(np.float32)
    labels = np.tile(np.arange(6), 6)
    features[np.arange(36), labels] += 3
    model = make_classifier(1.0, max_iter=500)
    model.fit(features, labels)
    probabilities = aligned_proba(model, features[:6], n_classes=6)
    assert probabilities.shape == (6, 6)
    np.testing.assert_allclose(probabilities.sum(axis=1), 1, atol=1e-5)
    assert probabilities.argmax(axis=1).tolist() == labels[:6].tolist()
