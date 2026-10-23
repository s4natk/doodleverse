from fastapi import FastAPI

from doodleverse.classes import LABELS

app = FastAPI(title="Doodleverse inference")


@app.get("/")
def root() -> dict[str, object]:
    return {
        "service": "doodleverse-inference",
        "labels": list(LABELS),
        "model_loaded": False,
    }
