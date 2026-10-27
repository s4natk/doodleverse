"""The exported CNN behind one call: strokes in; label, top three, and the gate's verdict out."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np

from doodleverse.classes import LABELS
from doodleverse.gate import accept
from doodleverse.preprocess.bitmap import INPUT_SIZE
from doodleverse.preprocess.strokes import RASTER_SIZE, strokes_to_model_input

SIDECAR_FILE = "sidecar.json"


class ModelContractError(RuntimeError):
    """The exported files do not match what this code can serve."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_sidecar(model_dir: Path) -> dict:
    """The sidecar, after checking it against the label order, input contract, and model file."""

    sidecar = json.loads((model_dir / SIDECAR_FILE).read_text(encoding="utf-8"))
    problems = []
    if sidecar["labels"] != list(LABELS):
        problems.append(f"labels {sidecar['labels']} are not {list(LABELS)}")
    if sidecar["input"]["size"] != INPUT_SIZE or sidecar["input"]["polarity"] != "ink_high":
        problems.append(f"input {sidecar['input']} is not {INPUT_SIZE}×{INPUT_SIZE} ink_high")
    if sidecar["rasterizer"]["raster_size"] != RASTER_SIZE:
        problems.append(f"raster size {sidecar['rasterizer']['raster_size']} is not {RASTER_SIZE}")
    if _sha256(model_dir / sidecar["model_file"]) != sidecar["sha256"]:
        problems.append(f"{sidecar['model_file']} does not match the SHA-256 in {SIDECAR_FILE}")
    if problems:
        raise ModelContractError(f"Cannot serve {model_dir}: " + "; ".join(problems) + ".")
    return sidecar


class Predictor:
    def __init__(self, model_dir: Path) -> None:
        import tensorflow as tf

        self.sidecar = read_sidecar(model_dir)
        self.version = f"{self.sidecar['variant']}-{self.sidecar['sha256'][:12]}"
        self.stroke_width = int(self.sidecar["rasterizer"]["stroke_width"])
        self.pad_fraction = float(self.sidecar["rasterizer"]["pad_fraction"])
        self.min_score = float(self.sidecar["gate"]["min_score"])
        self.min_margin = float(self.sidecar["gate"]["min_margin"])
        model = tf.keras.models.load_model(model_dir / self.sidecar["model_file"], compile=False)
        # One traced graph with a fixed signature. An eager Keras call spends about 6 ms per
        # drawing in overhead; the graph takes under 1 ms.
        self._forward = tf.function(
            lambda batch: model(batch, training=False),
            input_signature=[tf.TensorSpec([None, INPUT_SIZE, INPUT_SIZE, 1], tf.float32)],
        )
        self._forward(tf.zeros([1, INPUT_SIZE, INPUT_SIZE, 1], tf.float32))

    def rasterize(self, strokes: list, width: int, height: int) -> np.ndarray:
        return strokes_to_model_input(strokes, width, height, self.stroke_width, self.pad_fraction)

    def probabilities(self, tensor: np.ndarray) -> np.ndarray:
        return np.asarray(self._forward(tensor))[0]

    def predict(self, strokes: list, width: int, height: int) -> dict:
        started = time.perf_counter()
        probs = self.probabilities(self.rasterize(strokes, width, height))
        order = np.argsort(-probs, kind="stable")[:3]
        top3 = [{"label": LABELS[index], "score": float(probs[index])} for index in order]
        return {
            "label": top3[0]["label"],
            "score": top3[0]["score"],
            "top3": top3,
            "uncertain": not bool(accept(probs[None, :], self.min_score, self.min_margin)[0]),
            "model_version": self.version,
            "latency_ms": (time.perf_counter() - started) * 1000,
        }

    def info(self) -> dict:
        sidecar = self.sidecar
        test = sidecar.get("test")
        test_keys = ("count", "accuracy", "macro_f1", "gate_coverage", "gate_accepted_accuracy")
        return {
            "model_version": self.version,
            "variant": sidecar["variant"],
            "filters": sidecar["filters"],
            "parameter_count": sidecar["parameter_count"],
            "file_bytes": sidecar["file_bytes"],
            "sha256": sidecar["sha256"],
            "labels": sidecar["labels"],
            "input": sidecar["input"],
            "rasterizer": sidecar["rasterizer"],
            "gate": sidecar["gate"],
            "validation": sidecar["validation"],
            "test": None if test is None else {key: test[key] for key in test_keys},
            "tensorflow": sidecar["tensorflow"],
            "git": sidecar["git"],
        }
