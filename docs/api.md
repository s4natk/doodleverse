# Inference API

`services/inference` serves the frozen CNN in `artifacts/model`: `model.keras` plus `sidecar.json`, written by `python -m doodleverse.training.export`.

```bash
uvicorn doodleverse_api.main:app --port 8000
```

## Endpoints

`GET /health`

```json
{"status": "ok", "model_version": "gap-1ce366c1a170"}
```

`GET /model/info` returns the sidecar: labels in softmax order, the input contract, rasterizer settings, gate thresholds, parameter count, file size and SHA-256, validation and test metrics, and the git commit the export came from.

`POST /predict`

```json
{
  "canvas": {"width": 400, "height": 400},
  "strokes": [[[260, 200], [257, 222], [247, 241]], [[280, 200], [325, 200]]]
}
```

Points are `[x, y]` in canvas pixels, one list per stroke. The canvas size is validated but does not move the drawing: strokes are framed by their own bounding box before the 28×28 raster.

```json
{
  "label": "sun",
  "score": 0.983,
  "top3": [
    {"label": "sun", "score": 0.983},
    {"label": "flower", "score": 0.008},
    {"label": "cat", "score": 0.005}
  ],
  "uncertain": false,
  "model_version": "gap-1ce366c1a170",
  "latency_ms": 2.9
}
```

`uncertain` is true when the sidecar's gate rejects the prediction. For this model that means the top score leads the second by less than 0.70. An uncertain result should go back to the person as a choice, not be placed. Scores are softmax outputs, not calibrated probabilities.

## Errors

Every error is `{"error": {"code": ..., "message": ..., "details": [...]}}`. Details name the field and the problem. Submitted values are never echoed back or logged.

| status | code | when |
| --- | --- | --- |
| 422 | `invalid_json` | the body is not JSON |
| 422 | `invalid_request` | not an object, or a field the schema does not have |
| 422 | `invalid_canvas` | width or height missing, not an integer, or outside 1–8192 |
| 422 | `invalid_strokes` | strokes is not a list of lists |
| 422 | `invalid_point` | a point is not an `[x, y]` pair of finite numbers |
| 422 | `coordinate_out_of_range` | a coordinate is beyond ±1,000,000 |
| 422 | `empty_sketch` | no strokes |
| 422 | `empty_stroke` | a stroke with no points |
| 422 | `too_many_strokes` | more than 64 strokes |
| 422 | `too_many_points` | more than 4,096 points in total |
| 413 | `payload_too_large` | the body is over the byte limit, checked before parsing |
| 504 | `timeout` | the prediction ran past the timeout |
| 404, 405 | `not_found`, `method_not_allowed` | unknown route or method |

The 422 limits are the ones `doodleverse.preprocess.validate` enforces, so the schema and the rasterizer refuse the same sketches with the same codes.

## Settings

| variable | default |
| --- | --- |
| `DOODLEVERSE_MODEL_DIR` | `artifacts/model` |
| `DOODLEVERSE_CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` |
| `DOODLEVERSE_MAX_BODY_BYTES` | `262144` |
| `DOODLEVERSE_PREDICT_TIMEOUT_S` | `2.0` |

## Behavior

The model loads once, in the lifespan hook. The service refuses to start when the sidecar disagrees with the code: label order, 28×28 `ink_high` input, raster size, or the model file's SHA-256.

Strokes are rasterized with the sidecar's stroke width and pad, then run through a traced `tf.function` with a fixed input signature. Eager Keras calls spend most of their time in per-call overhead at batch size 1.

Each prediction logs one line: label, score, the uncertain flag, stroke and point counts, and latency. Coordinates are never logged.
