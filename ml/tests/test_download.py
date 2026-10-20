import numpy as np

from doodleverse.data.download import is_complete


def test_truncated_bitmap_is_not_complete(tmp_path):
    path = tmp_path / "sun.npy"
    np.save(path, np.zeros((8, 784), dtype=np.uint8))
    assert is_complete(path)
    path.write_bytes(path.read_bytes()[:-32])
    assert is_complete(path) is False
