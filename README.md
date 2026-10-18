# Doodleverse

Draw it. Bring it to life.

Doodleverse will be a small creative tool: a person sketches one object, a model trained on Google's Quick, Draw! drawings names it, and the browser turns that choice into something that moves in a pastel world. This checkout is only the Day 1 scaffold. There is no dataset, no trained model, and no drawing canvas yet.

## What is here

- `apps/web` — Next.js app shell. PixiJS 8, Matter.js, Vitest, and Playwright are installed and unused.
- `services/inference` — FastAPI process shell. It does not classify sketches.
- `ml/doodleverse` — Python package. The only contract so far is the label order in `classes.py`.
- `infra/docker-compose.yml` — two local services, not a finished deployment.
- `docs/architecture.md` — where classification will live, and where the world will live.

## Dataset

The six classes are sun, cloud, tree, flower, car, and cat, from the Quick, Draw! dataset by Google Creative Lab, CC BY 4.0. See [NOTICE](NOTICE). Do not commit the bitmap files.

## Label order

`sun`, `cloud`, `tree`, `flower`, `car`, `cat`. That tuple is the index order a later model must keep. Index 0 will be the first softmax unit. Changing the order after training would rename every answer without changing a weight.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
cd apps/web
npm ci
npm run dev
```

The API shell, from the repo root:

```bash
uvicorn doodleverse_api.main:app --app-dir services/inference --port 8000
```

Pins were checked against the current stable releases on 18 October 2026: Next.js 16.4.2, PixiJS 8.22.0, Matter.js 0.20.0, TensorFlow 2.21.0, FastAPI 0.146.0, scikit-learn 1.9.1. TypeScript is pinned to 5.9.3, which installs cleanly with this Next.js release. The newest TypeScript tag was 7.0.2 and was not used. OpenCV is pinned to the 4.14 line; the 5.0 package was left out so later image code is not written against an untested API.

## Not built yet

Download and splits, preprocessing, the logistic regression baseline, the CNN, prediction endpoints, the sketch canvas, and the animated world. Those are later days.
