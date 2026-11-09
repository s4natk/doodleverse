# Benchmark results

Written by `python -m bench.report` from [bench/results/api.json](../bench/results/api.json) and [bench/results/fps.json](../bench/results/fps.json). To measure again, run `python -m bench.api --container --url <api>` and `npm run bench` in `apps/web`.

## Model and API

Measured at commit `fcc0254` on AMD Ryzen 9 7945HX with Radeon Graphics, 32 logical CPUs, 31.7 GiB, Windows-11-10.0.26300-SP0. python 3.12.3, tensorflow 2.21.0, keras 3.15.1, numpy 2.5.4, opencv-python-headless 4.14.0.94, fastapi 0.146.0, uvicorn 0.54.0.

- Model file: `artifacts/model/model.keras`, 433,944 bytes (424 KB), 94,118 parameters, version `gap-1ce366c1a170`.
- Cold start, median of 3 fresh processes: 3.05 s to import TensorFlow and the service, 0.15 s to load and check the model, 2.5 ms for the first prediction.
- Ready to answer `/health` after starting: 4.1 s for a local uvicorn, 5.0 s for the container from `docker compose up`.

Warm `POST /predict`, one request at a time: 300 requests after 30 to warm up, cycling through 4 drawings of 231 to 367 points on a 652×489 canvas. Round trip is what the client measured. Predictor is the time the service reports spending in the predictor: rasterizing, the forward pass, and the gate.

| service | round trip p50 | round trip p95 | predictor p50 | predictor p95 |
| --- | --- | --- | --- | --- |
| local uvicorn, one process | 2.86 ms | 3.47 ms | 1.81 ms | 2.29 ms |
| Compose container | 4.15 ms | 4.73 ms | 2.42 ms | 2.82 ms |
| deployed | 24.71 ms | 25.55 ms | 3.42 ms | 4.06 ms |

The container ran under Docker 29.4.3 on Docker Desktop (kernel 6.6.87.2-microsoft-standard-WSL2), in a VM with 32 CPUs and 15.5 GiB. It used 237 MiB after starting and 229 MiB after the requests, as `docker stats` counts it. The cgroup's high-water mark was 696 MiB; that one counts page cache, such as TensorFlow's libraries read from the image, which the kernel can reclaim. The image is 2.44 GB on disk and 485 MB compressed.

Deployed means ECS Express Mode in us-east-2: one Fargate task, 512 CPU units (half a vCPU) and 1024 MiB, serving `gap-1ce366c1a170`, called from the machine above over its internet connection. Its round trip includes that network; its predictor time is the deployed task's own.

## Browser frame rate

Measured at commit `7db24eb` on AMD Ryzen 9 7945HX with Radeon Graphics, 32 logical CPUs, 31.7 GiB, Windows 11 Home 10.0.26300. Headed chromium 156.0.8078.4 on ANGLE (NVIDIA, NVIDIA GeForce RTX 4080 Laptop GPU (0x000027E0) Direct3D11 vs_5_0 ps_5_0, D3D11), Pixi's webgl renderer, a 1280×900 viewport at device pixel ratio 1, a 652×489 world canvas. node 24.22.0, next 16.4.2, react 19.3.1, pixi.js 8.22.0, matter-js 0.20.0, @playwright/test 1.64.1.

3 s to settle, then 10 s of requestAnimationFrame timestamps. Entities are spawned through the scene, not drawn, and every cloud is raining.

| entities | fps | frame p50 | frame p95 | slowest frame | main thread busy |
| --- | --- | --- | --- | --- | --- |
| 0 | 165.0 | 6.10 ms | 6.20 ms | 6.5 ms | 3.2% |
| 24: 4 of each class, 4 raining clouds, 7 physics bodies | 165.0 | 6.10 ms | 6.20 ms | 6.3 ms | 10.4% |

Both runs hold 165 fps, as many frames as the browser gave even the empty world, so frame rate alone cannot show what the world costs. The main thread's busy share can: 3.2% for the empty world, 10.4% with 24 entities.
