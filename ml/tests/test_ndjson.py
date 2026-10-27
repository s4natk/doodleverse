import json

import pytest

from doodleverse.data.ndjson import read_drawings, to_strokes


def _line(word: str, offset: int) -> bytes:
    drawing = [[[offset, offset + 10], [0, 5]], [[3], [4]]]
    return (json.dumps({"word": word, "recognized": True, "drawing": drawing}) + "\n").encode()


class _Response:
    """Yields lines and fails if read past `limit`, so a test can prove the reader stopped."""

    def __init__(self, lines: list[bytes], limit: int) -> None:
        self.lines = lines
        self.limit = limit

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def __iter__(self):
        for index, line in enumerate(self.lines):
            if index >= self.limit:
                raise AssertionError("read past the last needed line")
            yield line


def test_strokes_come_out_as_point_lists():
    assert to_strokes([[[1, 2], [3, 4]], [[5], [6]]]) == [[(1.0, 3.0), (2.0, 4.0)], [(5.0, 6.0)]]


def test_manifest_rows_are_skipped_and_reading_stops_once_enough_arrive(tmp_path):
    lines = [_line("sun", index) for index in range(10)]
    opened = []

    def opener(url):
        opened.append(url)
        return _Response(lines, limit=5)

    drawings = read_drawings("sun", 3, {1, 2}, tmp_path, opener=opener)
    assert [index for index, _ in drawings] == [0, 3, 4]
    assert drawings[1][1][0] == [(3.0, 0.0), (13.0, 5.0)]
    assert opened == ["https://storage.googleapis.com/quickdraw_dataset/full/simplified/sun.ndjson"]
    assert len((tmp_path / "sun.ndjson").read_bytes().splitlines()) == 5


def test_a_rerun_reads_the_cache_and_stays_offline(tmp_path):
    lines = [_line("cat", index) for index in range(6)]
    read_drawings("cat", 4, {0}, tmp_path, opener=lambda url: _Response(lines, limit=6))

    def offline(url):
        raise AssertionError("network used")

    again = read_drawings("cat", 4, {0}, tmp_path, opener=offline)
    assert [index for index, _ in again] == [1, 2, 3, 4]


def test_wrong_word_and_short_file_are_errors(tmp_path):
    with pytest.raises(ValueError, match="'cat' drawing"):
        read_drawings("sun", 1, set(), tmp_path, opener=lambda url: _Response([_line("cat", 0)], limit=1))
    with pytest.raises(RuntimeError, match="ended after 2"):
        read_drawings("tree", 3, set(), tmp_path, opener=lambda url: _Response([_line("tree", 0)] * 2, limit=2))
