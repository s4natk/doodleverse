import pytest

from bench.report import report

MACHINE = {"os": "Windows-11", "cpu": "Test CPU", "logical_cpus": 8, "memory_gib": 16.0}
LATENCY = {"round_trip_ms": {"p50": 3.05, "p95": 4.09}, "predictor_ms": {"p50": 1.89, "p95": 2.45}}


@pytest.fixture
def api():
    return {
        "git": {"commit": "abcdef1234567", "dirty": False},
        "machine": MACHINE,
        "versions": {"python": "3.12.3", "tensorflow": "2.21.0", "fastapi": "0.146.0"},
        "model": {"path": "artifacts/model/model.keras", "bytes": 433944, "parameters": 94118, "version": "gap-x"},
        "canvas": {"width": 652, "height": 489},
        "sketches": [{"points": 231}, {"points": 367}],
        "load": {
            "runs": 3,
            "import_s": {"median": 3.13},
            "load_s": {"median": 0.17},
            "first_predict_ms": {"median": 3.1},
        },
        "local": {"ready_s": 4.1, "requests": 300, "warmup": 30, **LATENCY},
        "container": {
            "ready_s": 3.8,
            "engine": {"docker": "29.4.3", "os": "Docker Desktop", "kernel": "6.6", "cpus": 32, "memory_gib": 15.5},
            "memory_bytes": {"after_start": 222 * 2**20, "after_requests": 223 * 2**20, "cgroup_peak": None},
            "image": {"disk_usage_bytes": 2_380_000_000, "content_bytes": None},
            **LATENCY,
        },
        "remote": {"url": "https://api.example", "server": "Fargate, half a vCPU", "model_version": "gap-x", **LATENCY},
    }


@pytest.fixture
def fps():
    frame = {"p50": 6.1, "p95": 6.2, "max": 6.5}
    return {
        "git": {"commit": "7db24eb000000", "dirty": False},
        "machine": MACHINE,
        "browser": {"name": "chromium", "version": "156", "headless": False, "gpu": "Test GPU", "renderer": "webgl"},
        "page": {"viewport": [1280, 900], "device_pixel_ratio": 1, "world_canvas": [652, 489]},
        "versions": {"node": "24.22.0", "pixi.js": "8.22.0"},
        "method": "3 s to settle, then 10 s of frames.",
        "runs": [
            {"entities": 0, "fps": 165.0, "frame_ms": frame, "main_thread_busy": 0.032},
            {
                "entities": 24,
                "per_class": 4,
                "raining_clouds": 4,
                "physics_bodies": 7,
                "fps": 164.9,
                "frame_ms": frame,
                "main_thread_busy": 0.104,
            },
        ],
    }


def test_every_table_names_where_it_was_measured(api, fps):
    page = report(api, fps)
    assert page.count("on Test CPU, 8 logical CPUs, 16.0 GiB, Windows-11") == 2
    assert "Measured at commit `abcdef1`" in page
    assert "python 3.12.3, tensorflow 2.21.0, fastapi 0.146.0" in page
    assert "Headed chromium 156 on Test GPU" in page


def test_the_numbers_land_in_their_rows(api, fps):
    page = report(api, fps)
    assert "| local uvicorn, one process | 3.05 ms | 4.09 ms | 1.89 ms | 2.45 ms |" in page
    assert "| deployed | 3.05 ms |" in page
    assert "Fargate, half a vCPU" in page
    assert "222 MiB after starting" in page and "high-water mark was not read" in page
    assert "| 24: 4 of each class, 4 raining clouds, 7 physics bodies | 164.9 |" in page
    assert "Both runs hold 165 fps" in page and "10.4% with 24 entities" in page


def test_the_container_and_deployed_rows_are_optional(api, fps):
    page = report({**api, "container": None, "remote": None}, fps)
    assert "Compose container" not in page and "| deployed |" not in page
    assert "for a local uvicorn." in page
