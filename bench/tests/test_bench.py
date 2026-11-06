import math

import pytest

from bench.api import CANVAS, POINT_SPACING, SKETCHES, logged_load_ms, parse_size, summarize
from bench.machine import machine, rounded, versions
from doodleverse.preprocess.validate import validate_sketch


def test_percentiles_interpolate_like_numpy():
    summary = summarize([float(value) for value in range(1, 101)])
    assert summary["p50"] == pytest.approx(50.5)
    assert summary["p95"] == pytest.approx(95.05)
    assert summary["mean"] == pytest.approx(50.5)
    assert summary["max"] == 100.0


def test_sizes_the_docker_cli_prints():
    assert parse_size("312.4MiB / 15.46GiB") == round(312.4 * 1024**2)
    assert parse_size("1.5GiB") == round(1.5 * 1024**3)
    assert parse_size("820kB") == 820_000
    assert parse_size("0B / 0B") == 0
    with pytest.raises(ValueError):
        parse_size("--")


def test_the_load_time_comes_from_the_service_log():
    log = "2026-11-06 09:00:01 INFO doodleverse_api model loaded version=gap-1ce366c1a170 load_ms=612\n"
    assert logged_load_ms(log) == 612.0
    assert logged_load_ms("Uvicorn running on http://127.0.0.1:8000") is None


def test_sketches_are_requests_the_service_accepts():
    for name, strokes in SKETCHES.items():
        cleaned = validate_sketch(strokes, CANVAS["width"], CANVAS["height"])
        assert 100 <= sum(len(stroke) for stroke in cleaned) <= 400, name
        for stroke in cleaned:
            assert all(0 <= x <= CANVAS["width"] and 0 <= y <= CANVAS["height"] for x, y in stroke), name
            steps = [math.dist(a, b) for a, b in zip(stroke, stroke[1:])]
            assert max(steps) <= POINT_SPACING + 0.2, name


def test_machine_and_versions_name_what_ran():
    info = machine()
    assert info["cpu"] and info["os"]
    assert info["logical_cpus"] >= 1
    assert info["memory_gib"] is None or info["memory_gib"] > 0
    assert set(versions("pytest", "not-a-real-distribution")) == {"python", "pytest"}


def test_results_are_rounded_all_the_way_down():
    assert rounded({"a": [1.23456, {"b": 2.0004}], "c": 3, "d": "x"}) == {"a": [1.235, {"b": 2.0}], "c": 3, "d": "x"}
