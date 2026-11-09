"""Write docs/benchmark-results.md from bench/results, with the machine and versions beside every number.

    python -m bench.report
"""

from __future__ import annotations

import json
from pathlib import Path

from bench.machine import RESULTS_DIR, ROOT

API_VERSIONS = (
    "python",
    "tensorflow",
    "tensorflow-cpu",
    "keras",
    "numpy",
    "opencv-python-headless",
    "fastapi",
    "uvicorn",
)
WEB_VERSIONS = ("node", "next", "react", "pixi.js", "matter-js", "@playwright/test")


def _ms(value: float) -> str:
    return f"{value:.2f} ms"


def _mib(value: int | None) -> str:
    return "not read" if value is None else f"{value / 2**20:,.0f} MiB"


def _versions(versions: dict, names: tuple[str, ...]) -> str:
    return ", ".join(f"{name} {versions[name]}" for name in names if name in versions)


def _measured(results: dict) -> str:
    machine, git = results["machine"], results["git"]
    commit = f"commit `{git['commit'][:7]}`" + (" with uncommitted changes" if git["dirty"] else "")
    return (
        f"Measured {results['date']} at {commit} on {machine['cpu']}, {machine['logical_cpus']} logical CPUs, "
        f"{machine['memory_gib']} GiB, {machine['os']}"
    )


def _latency_row(name: str, run: dict) -> str:
    trip, inside = run["round_trip_ms"], run["predictor_ms"]
    return f"| {name} | {_ms(trip['p50'])} | {_ms(trip['p95'])} | {_ms(inside['p50'])} | {_ms(inside['p95'])} |"


def api_section(api: dict) -> list[str]:
    model, load, local, container, remote = api["model"], api["load"], api["local"], api["container"], api["remote"]
    points = [sketch["points"] for sketch in api["sketches"]]
    canvas = api["canvas"]
    lines = [
        "## Model and API",
        "",
        f"{_measured(api)}. {_versions(api['versions'], API_VERSIONS)}.",
        "",
        f"- Model file: `{model['path']}`, {model['bytes']:,} bytes ({model['bytes'] / 1024:,.0f} KB), "
        f"{model['parameters']:,} parameters, version `{model['version']}`.",
        f"- Cold start, median of {load['runs']} fresh processes: {load['import_s']['median']:.2f} s to import "
        f"TensorFlow and the service, {load['load_s']['median']:.2f} s to load and check the model, "
        f"{load['first_predict_ms']['median']:.1f} ms for the first prediction.",
        f"- Ready to answer `/health` after starting: {local['ready_s']:.1f} s for a local uvicorn"
        + (f", {container['ready_s']:.1f} s for the container from `docker compose up`" if container else "")
        + ".",
        "",
        f"Warm `POST /predict`, one request at a time: {local['requests']} requests after {local['warmup']} to warm "
        f"up, cycling through {len(points)} drawings of {min(points)} to {max(points)} points on a "
        f"{canvas['width']}×{canvas['height']} canvas. Round trip is what the client measured. Predictor is the time "
        "the service reports spending in the predictor: rasterizing, the forward pass, and the gate.",
        "",
        "| service | round trip p50 | round trip p95 | predictor p50 | predictor p95 |",
        "| --- | --- | --- | --- | --- |",
        _latency_row("local uvicorn, one process", local),
    ]
    if container:
        lines.append(_latency_row("Compose container", container))
    if remote:
        lines.append(_latency_row("deployed", remote))
    if container:
        engine, memory, image = container["engine"], container["memory_bytes"], container["image"]
        lines += [
            "",
            f"The container ran under Docker {engine['docker']} on {engine['os']} (kernel {engine['kernel']}), in a "
            f"VM with {engine['cpus']} CPUs and {engine['memory_gib']} GiB. It used {_mib(memory['after_start'])} "
            f"after starting and {_mib(memory['after_requests'])} after the requests, as `docker stats` counts it. "
            f"The cgroup's high-water mark was {_mib(memory['cgroup_peak'])}; that one counts page cache, such as "
            "TensorFlow's libraries read from the image, which the kernel can reclaim. The image is "
            f"{image['disk_usage_bytes'] / 1e9:.2f} GB on disk"
            + (f" and {image['content_bytes'] / 1e6:,.0f} MB compressed." if image["content_bytes"] else ".")
        ]
    if remote:
        lines += [
            "",
            f"Deployed means {remote['server'] or remote['url']}, serving `{remote['model_version']}`, called from the "
            "machine above over its internet connection. Its round trip includes that network; its predictor time "
            "is the deployed task's own.",
        ]
    return lines


def fps_section(fps: dict) -> list[str]:
    browser, page = fps["browser"], fps["page"]
    empty, full = fps["runs"][0], fps["runs"][-1]
    viewport, world = page["viewport"], page["world_canvas"]
    mode = "headless" if browser["headless"] else "headed"
    versions = _versions(fps["versions"], WEB_VERSIONS)
    lines = [
        "## Browser frame rate",
        "",
        f"{_measured(fps)}. {mode.capitalize()} {browser['name']} {browser['version']} on {browser['gpu']}, Pixi's "
        f"{browser['renderer']} renderer, a {viewport[0]}×{viewport[1]} viewport at device pixel ratio "
        f"{page['device_pixel_ratio']}, a {world[0]}×{world[1]} world canvas. {versions}.",
        "",
        fps["method"],
        "",
        "| entities | fps | frame p50 | frame p95 | slowest frame | main thread busy |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for run in fps["runs"]:
        name = str(run["entities"])
        if run.get("per_class"):
            name += (
                f": {run['per_class']} of each class, {run['raining_clouds']} raining clouds, "
                f"{run['physics_bodies']} physics bodies"
            )
        frame = run["frame_ms"]
        lines.append(
            f"| {name} | {run['fps']:.1f} | {_ms(frame['p50'])} | {_ms(frame['p95'])} | {frame['max']:.1f} ms | "
            f"{run['main_thread_busy']:.1%} |"
        )
    if abs(full["fps"] - empty["fps"]) <= 0.01 * empty["fps"]:
        lines += [
            "",
            f"Both runs hold {empty['fps']:.0f} fps, as many frames as the browser gave even the empty world, so frame "
            "rate alone cannot show what the world costs. The main thread's busy share can: "
            f"{empty['main_thread_busy']:.1%} for the empty world, {full['main_thread_busy']:.1%} with "
            f"{full['entities']} entities.",
        ]
    return lines


def report(api: dict, fps: dict) -> str:
    lines = [
        "# Benchmark results",
        "",
        "Written by `python -m bench.report` from [bench/results/api.json](../bench/results/api.json) and "
        "[bench/results/fps.json](../bench/results/fps.json). To measure again, run "
        "`python -m bench.api --container --url <api>` and `npm run bench` in `apps/web`.",
        "",
        *api_section(api),
        "",
        *fps_section(fps),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Write the benchmark page from bench/results.")
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "benchmark-results.md")
    args = parser.parse_args()

    def read(name: str) -> dict:
        return json.loads((RESULTS_DIR / name).read_text(encoding="utf-8"))

    args.out.write_text(report(read("api.json"), read("fps.json")), encoding="utf-8")
    print(f"wrote {args.out.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
