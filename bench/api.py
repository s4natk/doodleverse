"""Model bytes, cold load time, and warm /predict latency, locally and in the Compose container.

    python -m bench.api                # artifacts/model behind a local uvicorn
    python -m bench.api --container    # then the inference service from infra/docker-compose.yml as well
    python -m bench.api --url URL      # and a service that is already running somewhere, such as the deployed one

Writes bench/results/api.json with the machine and versions beside the numbers. Requests go one at a time.
"""

from __future__ import annotations

import json
import math
import os
import re
import socket
import statistics
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from datetime import date
from pathlib import Path

from bench.machine import RESULTS_DIR, ROOT, git_state, machine, versions, write_results

COMPOSE = ROOT / "infra" / "docker-compose.yml"
SERVICE = "inference"
CONTAINER_URL = "http://127.0.0.1:8000"
DISTRIBUTIONS = (
    "tensorflow",
    "tensorflow-cpu",
    "keras",
    "numpy",
    "opencv-python-headless",
    "fastapi",
    "uvicorn",
    "pydantic",
    "httpx",
)
# The drawing area of a 1280-pixel-wide window.
CANVAS = {"width": 652, "height": 489}
# The browser drops points closer than 1.5 px; a stroke at drawing speed lands them a few pixels apart.
POINT_SPACING = 3.0


def _line(corners: list[tuple[float, float]], spacing: float = POINT_SPACING) -> list[list[float]]:
    """A polyline through `corners`, filled in every `spacing` pixels the way pointer events arrive."""

    points = [[round(corners[0][0], 1), round(corners[0][1], 1)]]
    for (x0, y0), (x1, y1) in zip(corners, corners[1:]):
        steps = max(1, math.ceil(math.hypot(x1 - x0, y1 - y0) / spacing))
        for step in range(1, steps + 1):
            t = step / steps
            points.append([round(x0 + (x1 - x0) * t, 1), round(y0 + (y1 - y0) * t, 1)])
    return points


def _arc(cx: float, cy: float, rx: float, ry: float, start: float = 0.0, end: float = 2 * math.pi):
    angles = [start + (end - start) * i / 48 for i in range(49)]
    return [(cx + rx * math.cos(angle), cy + ry * math.sin(angle)) for angle in angles]


def _sketches() -> dict[str, list[list[list[float]]]]:
    sun = [_line(_arc(180, 150, 50, 50))]
    for k in range(8):
        angle = 2 * math.pi * k / 8
        inner = (180 + 65 * math.cos(angle), 150 + 65 * math.sin(angle))
        outer = (180 + 100 * math.cos(angle), 150 + 100 * math.sin(angle))
        sun.append(_line([inner, outer]))
    cloud = [
        _line(
            _arc(230, 170, 50, 50, math.pi, 1.75 * math.pi)
            + _arc(305, 145, 60, 60, 1.15 * math.pi, 1.9 * math.pi)
            + _arc(375, 170, 45, 45, 1.3 * math.pi, 2 * math.pi)
            + [(420, 190), (180, 190), (180, 170)]
        )
    ]
    tree = [_line([(310, 430), (310, 330)]), _line([(332, 430), (332, 330)]), _line(_arc(321, 270, 70, 65))]
    body = [(160, 400), (480, 400), (480, 350), (400, 350), (370, 300), (250, 300), (220, 350), (160, 350), (160, 400)]
    car = [_line(body), _line(_arc(230, 410, 22, 22)), _line(_arc(410, 410, 22, 22))]
    return {"sun": sun, "cloud": cloud, "tree": tree, "car": car}


SKETCHES = _sketches()


def summarize(values: list[float]) -> dict:
    """p50, p95, mean, and max. The percentiles interpolate the way numpy's default does."""

    cuts = statistics.quantiles(values, n=100, method="inclusive")
    return {"p50": cuts[49], "p95": cuts[94], "mean": statistics.fmean(values), "max": max(values)}


_UNITS = {
    "B": 1,
    "kB": 1000,
    "KB": 1000,
    "MB": 1000**2,
    "GB": 1000**3,
    "KiB": 1024,
    "MiB": 1024**2,
    "GiB": 1024**3,
    "TiB": 1024**4,
}


def parse_size(text: str) -> int:
    """Bytes in the first size the docker CLI prints in `text`, such as `312.4MiB / 15.46GiB`."""

    match = re.search(r"(\d+(?:\.\d+)?)\s*([kKMGT]?i?B)\b", text)
    if not match or match.group(2) not in _UNITS:
        raise ValueError(f"No size in {text!r}.")
    return round(float(match.group(1)) * _UNITS[match.group(2)])


def logged_load_ms(log: str) -> float | None:
    """The load time the service logs once its model is ready."""

    match = re.search(r"model loaded .*load_ms=(\d+)", log)
    return float(match.group(1)) if match else None


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def model_files(model_dir: Path) -> dict:
    sidecar_path = model_dir / "sidecar.json"
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    model_path = model_dir / sidecar["model_file"]
    return {
        "path": _relative(model_path),
        "bytes": model_path.stat().st_size,
        "sidecar_bytes": sidecar_path.stat().st_size,
        "version": f"{sidecar['variant']}-{sidecar['sha256'][:12]}",
        "parameters": sidecar["parameter_count"],
    }


def _quiet_env(**extra: str) -> dict:
    return {**os.environ, "TF_CPP_MIN_LOG_LEVEL": "2", **extra}


def _run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    # BuildKit progress and TensorFlow logs are UTF-8 whatever the console code page is.
    return subprocess.run(command, capture_output=True, encoding="utf-8", errors="replace", **kwargs)


def probe_load(model_dir: Path) -> dict:
    """One cold start in this fresh process: imports, building the Predictor, then the first prediction."""

    started = time.perf_counter()
    import tensorflow  # noqa: F401

    from doodleverse_api.predictor import Predictor

    imported = time.perf_counter()
    predictor = Predictor(model_dir)
    loaded = time.perf_counter()
    predictor.predict(SKETCHES["sun"], CANVAS["width"], CANVAS["height"])
    done = time.perf_counter()
    return {"import_s": imported - started, "load_s": loaded - imported, "first_predict_ms": (done - loaded) * 1000}


def cold_loads(model_dir: Path, runs: int) -> dict:
    """`probe_load` in `runs` fresh interpreters, so nothing is cached in-process between them."""

    samples = []
    probe = [sys.executable, "-m", "bench.api", "--probe-load", str(model_dir)]
    for _ in range(runs):
        completed = _run(probe, cwd=ROOT, env=_quiet_env())
        if completed.returncode != 0:
            raise RuntimeError(f"The load probe failed:\n{completed.stderr[-3000:]}")
        samples.append(json.loads(completed.stdout.strip().splitlines()[-1]))
    measured = {}
    for key in samples[0]:
        values = [sample[key] for sample in samples]
        measured[key] = {"median": statistics.median(values), "all": values}
    return {"runs": runs, **measured}


def wait_until_healthy(url: str, since: float, timeout_s: float, alive: Callable[[], bool] = lambda: True) -> float:
    """Seconds from `since` until GET /health answers 200."""

    import httpx

    while time.perf_counter() - since < timeout_s:
        if not alive():
            raise RuntimeError("The server exited before it was healthy.")
        try:
            if httpx.get(f"{url}/health", timeout=1.0).status_code == 200:
                return time.perf_counter() - since
        except httpx.TransportError:
            pass
        time.sleep(0.05)
    raise TimeoutError(f"{url}/health did not answer within {timeout_s:.0f} s.")


def warm_latency(url: str, warmup: int, requests: int) -> dict:
    """Round trip as the client sees it, and the time the service reports spending in the predictor."""

    import httpx

    payloads = [json.dumps({"canvas": CANVAS, "strokes": strokes}).encode() for strokes in SKETCHES.values()]
    round_trip: list[float] = []
    predictor: list[float] = []
    with httpx.Client(base_url=url, headers={"Content-Type": "application/json"}, timeout=10.0) as client:
        for index in range(warmup + requests):
            payload = payloads[index % len(payloads)]
            started = time.perf_counter()
            response = client.post("/predict", content=payload)
            elapsed_ms = (time.perf_counter() - started) * 1000
            response.raise_for_status()
            if index >= warmup:
                round_trip.append(elapsed_ms)
                predictor.append(response.json()["latency_ms"])
    return {
        "warmup": warmup,
        "requests": requests,
        "round_trip_ms": summarize(round_trip),
        "predictor_ms": summarize(predictor),
    }


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def run_local(model_dir: Path, warmup: int, requests: int) -> dict:
    port = _free_port()
    url = f"http://127.0.0.1:{port}"
    command = [sys.executable, "-m", "uvicorn", "doodleverse_api.main:app", "--host", "127.0.0.1"]
    command += ["--port", str(port), "--no-access-log"]
    with tempfile.TemporaryFile() as log:
        started = time.perf_counter()
        server = subprocess.Popen(
            command,
            cwd=ROOT,
            env=_quiet_env(DOODLEVERSE_MODEL_DIR=str(model_dir)),
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            ready_s = wait_until_healthy(url, started, 120, alive=lambda: server.poll() is None)
            numbers = warm_latency(url, warmup, requests)
        except Exception as error:
            log.seek(0)
            raise RuntimeError(f"{error}\n{log.read().decode('utf-8', errors='replace')[-3000:]}") from error
        finally:
            server.terminate()
            server.wait(timeout=30)
        log.seek(0)
        output = log.read().decode("utf-8", errors="replace")
    return {
        "server": "uvicorn, one process, 127.0.0.1",
        "ready_s": ready_s,
        "load_ms_logged": logged_load_ms(output),
        **numbers,
    }


def docker(*args: str) -> str:
    completed = _run(["docker", *args], cwd=ROOT)
    if completed.returncode != 0:
        raise RuntimeError(f"docker {' '.join(args)} failed:\n{completed.stderr.strip()[-3000:]}")
    return completed.stdout.strip()


def compose(*args: str) -> str:
    return docker("compose", "-f", str(COMPOSE), *args)


def container_logs(container: str) -> str:
    completed = _run(["docker", "logs", container])
    return completed.stdout + completed.stderr


def container_memory(container: str) -> int:
    """Memory in use as `docker stats` counts it: page cache that can be reclaimed is left out."""

    return parse_size(docker("stats", "--no-stream", "--format", "{{.MemUsage}}", container))


def container_peak(container: str) -> int | None:
    """The cgroup's high-water mark since the container started, page cache included."""

    try:
        return int(docker("exec", container, "cat", "/sys/fs/cgroup/memory.peak"))
    except (RuntimeError, ValueError):
        return None


def engine() -> dict:
    info = json.loads(docker("info", "--format", "{{json .}}"))
    containerd = any("containerd.snapshotter" in str(item) for item in info.get("DriverStatus") or [])
    return {
        "docker": docker("version", "--format", "{{.Server.Version}}"),
        "os": info["OperatingSystem"],
        "kernel": info["KernelVersion"],
        "cpus": info["NCPU"],
        "memory_gib": round(info["MemTotal"] / 2**30, 1),
        "image_store": "containerd" if containerd else info["Driver"],
    }


def image_sizes(image: str, store: str) -> dict:
    """Unpacked size on disk, as `docker image ls` shows it, and the compressed layers a pull downloads.

    `docker image inspect` reports the compressed size only with the containerd image store.
    """

    inspected = int(docker("image", "inspect", "--format", "{{.Size}}", image))
    return {
        "disk_usage_bytes": parse_size(docker("image", "ls", image, "--format", "{{.Size}}")),
        "content_bytes": inspected if store == "containerd" else None,
    }


def run_container(warmup: int, requests: int) -> dict:
    """A fresh container from the Compose file, timed from `up` to a healthy /health, then loaded."""

    print("building the inference image; unchanged layers come from the cache", flush=True)
    compose("build", SERVICE)
    docker_engine = engine()
    was_running = bool(compose("ps", "--quiet", SERVICE))
    started = time.perf_counter()
    compose("up", "--detach", "--force-recreate", "--no-deps", SERVICE)
    container = compose("ps", "--quiet", SERVICE)
    try:
        ready_s = wait_until_healthy(CONTAINER_URL, started, 180)
        after_start = container_memory(container)
        numbers = warm_latency(CONTAINER_URL, warmup, requests)
        after_requests = container_memory(container)
        peak = container_peak(container)
        image = docker("inspect", "--format", "{{.Config.Image}}", container)
        sizes = image_sizes(image, docker_engine["image_store"])
        load_ms = logged_load_ms(container_logs(container))
    finally:
        if not was_running:
            compose("rm", "--stop", "--force", SERVICE)
    return {
        "engine": docker_engine,
        "image": {"name": image, **sizes},
        "ready_s": ready_s,
        "load_ms_logged": load_ms,
        **numbers,
        "memory_bytes": {"after_start": after_start, "after_requests": after_requests, "cgroup_peak": peak},
    }


def run_remote(url: str, warmup: int, requests: int, note: str | None) -> dict:
    """A service someone else started. Its round trip includes the network between here and there."""

    import httpx

    url = url.rstrip("/")
    info = httpx.get(f"{url}/model/info", timeout=10.0).raise_for_status().json()
    return {"url": url, "server": note, "model_version": info["model_version"], **warm_latency(url, warmup, requests)}


def summary(results: dict) -> str:
    model, load, local = results["model"], results["load"], results["local"]
    lines = [
        f"model      {model['path']}: {model['bytes'] / 1024:,.0f} KB, {model['parameters']:,} parameters, "
        f"{model['version']}",
        f"cold start median of {load['runs']} fresh processes: imports {load['import_s']['median']:.2f} s, "
        f"load {load['load_s']['median']:.2f} s, first prediction {load['first_predict_ms']['median']:.1f} ms",
    ]
    runs = [("local", local)]
    if results["container"]:
        runs.append(("container", results["container"]))
    if results.get("remote"):
        runs.append(("remote", results["remote"]))
    for name, run in runs:
        trip, inside = run["round_trip_ms"], run["predictor_ms"]
        ready = f"ready in {run['ready_s']:.1f} s; " if "ready_s" in run else ""
        lines.append(
            f"{name:10s} {ready}{run['requests']} requests: round trip "
            f"p50 {trip['p50']:.2f} ms, p95 {trip['p95']:.2f} ms; predictor p50 {inside['p50']:.2f} ms, "
            f"p95 {inside['p95']:.2f} ms"
        )
    container = results["container"]
    if container:
        memory = container["memory_bytes"]
        peak = "" if memory["cgroup_peak"] is None else f", cgroup peak {memory['cgroup_peak'] / 2**20:,.0f} MiB"
        image = container["image"]
        compressed = "" if image["content_bytes"] is None else f", {image['content_bytes'] / 1e6:,.0f} MB compressed"
        lines.append(
            f"{'':10s} memory {memory['after_start'] / 2**20:,.0f} MiB after start, "
            f"{memory['after_requests'] / 2**20:,.0f} MiB after the requests{peak}; "
            f"image {image['disk_usage_bytes'] / 1e9:.2f} GB on disk{compressed}"
        )
    return "\n".join(lines)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark the frozen model and the /predict service.")
    parser.add_argument("--model-dir", type=Path, default=ROOT / "artifacts" / "model")
    parser.add_argument("--requests", type=int, default=300)
    parser.add_argument("--warmup", type=int, default=30)
    parser.add_argument("--load-runs", type=int, default=3)
    parser.add_argument("--container", action="store_true", help="also measure the Compose inference service")
    parser.add_argument("--url", help="also measure a service already running at this base URL")
    parser.add_argument("--url-note", help="what and where that service runs on, recorded with its numbers")
    parser.add_argument("--out", type=Path, default=RESULTS_DIR / "api.json")
    parser.add_argument("--probe-load", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.probe_load:
        print(json.dumps(probe_load(args.probe_load)))
        return
    results = {
        "benchmark": "api",
        "date": date.today().isoformat(),
        "git": git_state(),
        "machine": machine(),
        "versions": versions(*DISTRIBUTIONS),
        "model": model_files(args.model_dir),
        "canvas": CANVAS,
        "sketches": [
            {"name": name, "strokes": len(strokes), "points": sum(len(stroke) for stroke in strokes)}
            for name, strokes in SKETCHES.items()
        ],
        "load": cold_loads(args.model_dir, args.load_runs),
        "local": run_local(args.model_dir, args.warmup, args.requests),
        "container": run_container(args.warmup, args.requests) if args.container else None,
        "remote": run_remote(args.url, args.warmup, args.requests, args.url_note) if args.url else None,
    }
    write_results(args.out, results)
    print(summary(results))
    print(f"wrote {_relative(args.out)}")


if __name__ == "__main__":
    main()
