"""Process shell for the future sketch classifier.

This app does not load a model and does not accept drawings. It exists so the
Python side installs and Docker Compose has a process to start.
"""

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
