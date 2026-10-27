"""Quick, Draw! simplified drawings, streamed line by line from the public ndjson files.

Line i of `{label}.ndjson` is drawing i of `{label}.npy`, so manifest indices can be skipped here.
"""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable
from pathlib import Path

STROKES_URL = "https://storage.googleapis.com/quickdraw_dataset/full/simplified/{label}.ndjson"
# Simplified drawings are scaled so the longer side spans 0–255.
CANVAS_SIZE = 256

Strokes = list[list[tuple[float, float]]]


def to_strokes(drawing: list) -> Strokes:
    """`[[xs, ys], ...]` from the file into `[[(x, y), ...], ...]`."""

    return [list(zip(map(float, stroke[0]), map(float, stroke[1]))) for stroke in drawing]


def _unskipped(lines: list[bytes], wanted: int, skip: set[int]) -> list[tuple[int, bytes]]:
    picked = []
    for index, line in enumerate(lines):
        if index in skip or not line.strip():
            continue
        picked.append((index, line))
        if len(picked) == wanted:
            break
    return picked


def _stream(url: str, wanted: int, skip: set[int], opener: Callable) -> list[bytes]:
    """Every line up to the one that completes `wanted` unskipped drawings, then stop reading."""

    lines: list[bytes] = []
    found = 0
    with opener(url) as response:
        for line in response:
            lines.append(line.rstrip(b"\r\n"))
            if len(lines) - 1 not in skip and lines[-1].strip():
                found += 1
                if found == wanted:
                    break
    return lines


def _open(url: str):
    return urllib.request.urlopen(url, timeout=60)


def read_drawings(
    label: str,
    wanted: int,
    skip: set[int],
    cache_dir: Path,
    opener: Callable | None = None,
) -> list[tuple[int, Strokes]]:
    """First `wanted` drawings whose line index is not in `skip`, as `(index, strokes)`.

    The download stops as soon as enough lines arrive. Lines read are cached under `cache_dir`,
    skipped ones included so indices stay aligned, and a rerun with enough cached lines stays offline.
    """

    cache = cache_dir / f"{label}.ndjson"
    lines = cache.read_bytes().splitlines() if cache.exists() else []
    if len(_unskipped(lines, wanted, skip)) < wanted:
        lines = _stream(STROKES_URL.format(label=label), wanted, skip, opener or _open)
        cache.parent.mkdir(parents=True, exist_ok=True)
        partial = cache.with_suffix(".ndjson.partial")
        partial.write_bytes(b"\n".join(lines) + b"\n")
        partial.replace(cache)
    drawings = []
    for index, line in _unskipped(lines, wanted, skip):
        record = json.loads(line)
        if record["word"] != label:
            raise ValueError(f"Line {index} of {label}.ndjson is a {record['word']!r} drawing.")
        drawings.append((index, to_strokes(record["drawing"])))
    if len(drawings) < wanted:
        raise RuntimeError(f"{label}.ndjson ended after {len(drawings)} usable drawings; wanted {wanted}.")
    return drawings
