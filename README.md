# Doodleverse

Draw it. Bring it to life.

Draw an object and watch it take a place in a small animated world.

Sketches are named with a model trained on the [Quick, Draw!](https://github.com/googlecreativelab/quickdraw-dataset) dataset by Google Creative Lab, used under [CC BY 4.0](NOTICE).

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
python -m doodleverse.data.prepare
```

```bash
cd apps/web
npm ci
npm run dev
```
