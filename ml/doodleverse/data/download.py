"""Fetch only the six numpy bitmap files this project uses.

Each file is one class. The array is uint8 with shape (N, 784): N drawings,
each already scaled by Google into a 28×28 image and stored as one row.
"""

from __future__ import annotations

import ast
import struct
import urllib.request
from pathlib import Path

import numpy as np

from doodleverse.classes import LABELS

BITMAP_URL = "https://storage.googleapis.com/quickdraw_dataset/full/numpy_bitmap/{label}.npy"
_NPY_MAGIC = b"\x93NUMPY"


def bitmap_path(raw_dir: Path, label: str) -> Path:
    return raw_dir / f"{label}.npy"


def _declared_size(path: Path) -> int:
    """Byte length implied by the numpy header, including the header itself."""

    with path.open("rb") as handle:
        prefix = handle.read(16)
    if prefix[:6] != _NPY_MAGIC:
        raise ValueError(f"{path} is not a numpy file.")
    major = prefix[6]
    if major == 1:
        header_len = struct.unpack_from("<H", prefix, 8)[0]
        header_start = 10
    else:
        header_len = struct.unpack_from("<I", prefix, 8)[0]
        header_start = 12
    with path.open("rb") as handle:
        handle.seek(header_start)
        header = handle.read(header_len).decode("latin1").strip()
    meta = ast.literal_eval(header)
    rows, cols = meta["shape"]
    if meta["descr"] not in {"|u1", "<u1", "u1"} or int(cols) != 784:
        raise ValueError(f"{path} is not a uint8 bitmap of 784 pixels.")
    return header_start + header_len + int(rows) * int(cols)


def is_complete(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 128:
        return False
    try:
        return path.stat().st_size == _declared_size(path)
    except (OSError, ValueError, SyntaxError, KeyError):
        return False


def bitmap_row_count(path: Path) -> int:
    array = np.load(path, mmap_mode="r")
    if array.ndim != 2 or array.shape[1] != 784:
        raise ValueError(f"{path} has shape {array.shape}; expected (N, 784).")
    return int(array.shape[0])


def download_bitmaps(raw_dir: Path, labels: tuple[str, ...] = LABELS) -> dict[str, Path]:
    """Download missing category files. A complete .npy file is kept."""

    raw_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label in labels:
        if label not in LABELS:
            raise ValueError(f"{label} is not one of the six project classes.")
        target = bitmap_path(raw_dir, label)
        if is_complete(target):
            paths[label] = target
            continue
        url = BITMAP_URL.format(label=label)
        partial = target.with_suffix(".npy.partial")
        partial.unlink(missing_ok=True)
        urllib.request.urlretrieve(url, partial)
        if not is_complete(partial):
            partial.unlink(missing_ok=True)
            raise RuntimeError(f"Download for {label} was incomplete: {url}")
        partial.replace(target)
        paths[label] = target
    return paths
