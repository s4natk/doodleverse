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
pytest
```

```bash
cd apps/web
npm ci
npm run dev
```

Results are in [docs/experiments.md](docs/experiments.md).
