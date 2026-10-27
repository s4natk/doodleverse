# Doodleverse

Draw it. Bring it to life.

Draw an object and watch it take a place in a small animated world.

Sketches are named with a model trained on the [Quick, Draw!](https://github.com/googlecreativelab/quickdraw-dataset) dataset by Google Creative Lab, used under [CC BY 4.0](NOTICE).

## Run it

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m doodleverse.data.prepare          # download six classes, write the split
python -m doodleverse.training.compare      # train the baseline and the CNN
python -m doodleverse.training.select_cnn   # train the narrow CNN, keep one
python -m doodleverse.training.analyze      # validation mistakes and the uncertainty gate
python -m doodleverse.training.skew         # score held-out strokes through the rasterizer
python -m doodleverse.training.export       # artifacts/model: model.keras and sidecar.json
uvicorn doodleverse_api.main:app            # serve artifacts/model on :8000
pytest
```

```bash
cd apps/web
npm ci
npm run dev
```

Results are in [docs/experiments.md](docs/experiments.md). The test split has been scored once, and [ml/splits/v1.test-scored.json](ml/splits/v1.test-scored.json) keeps it that way. The service contract is in [docs/api.md](docs/api.md).
