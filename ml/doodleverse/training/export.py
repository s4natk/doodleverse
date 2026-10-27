"""Freeze the kept CNN: `model.keras` without optimizer state, plus `sidecar.json` for serving."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np

from doodleverse.classes import LABELS
from doodleverse.data.splits import read_manifest
from doodleverse.preprocess.bitmap import INPUT_SIZE
from doodleverse.preprocess.strokes import PAD_FRACTION, RASTER_SIZE, STROKE_WIDTH
from doodleverse.report import upsert_section

MODEL_FILE = "model.keras"
SIDECAR_FILE = "sidecar.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git_state() -> dict:
    """HEAD and whether the working tree had uncommitted changes. Both null outside a checkout."""

    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}
    return {"commit": head.stdout.strip(), "dirty": bool(status.stdout.strip())}


def check_reload(path: Path) -> np.ndarray:
    """Reload the export and require six probabilities per row that sum to 1."""

    import tensorflow as tf

    model = tf.keras.models.load_model(path, compile=False)
    probe = np.zeros((2, INPUT_SIZE, INPUT_SIZE, 1), dtype=np.float32)
    probe[1, 8:20, 8:20, 0] = 1.0
    probs = np.asarray(model(probe, training=False))
    if probs.shape != (2, len(LABELS)) or not np.allclose(probs.sum(axis=1), 1.0, atol=1e-5):
        raise RuntimeError(f"Reloaded export returned shape {probs.shape} with row sums {probs.sum(axis=1)}.")
    return probs


def build_sidecar(model_path: Path, report: dict, gate: dict, manifest_path: Path, manifest: dict) -> dict:
    import keras
    import tensorflow as tf

    return {
        "model_file": model_path.name,
        "sha256": sha256(model_path),
        "file_bytes": model_path.stat().st_size,
        "variant": report["variant"],
        "filters": report.get("filters", [32, 64, 128]),
        "parameter_count": report["parameter_count"],
        "labels": list(LABELS),
        "input": {
            "size": INPUT_SIZE,
            "channels": 1,
            "dtype": "float32",
            "range": [0.0, 1.0],
            "polarity": "ink_high",
        },
        "rasterizer": {"raster_size": RASTER_SIZE, "stroke_width": STROKE_WIDTH, "pad_fraction": PAD_FRACTION},
        "gate": {"min_score": gate["min_score"], "min_margin": gate["min_margin"], "target": gate["target"]},
        "validation": {
            "accuracy": report["val_accuracy"],
            "macro_f1": report["val_macro_f1"],
            "gate_coverage": gate["val_coverage"],
            "gate_accepted_accuracy": gate["val_accepted_accuracy"],
        },
        "test": None,
        "split": {
            "manifest": manifest_path.as_posix(),
            "seed": manifest["seed"],
            "samples_per_class": manifest["samples_per_class"],
        },
        "tensorflow": tf.__version__,
        "keras": keras.__version__,
        "git": git_state(),
    }


def export_section(sidecar: dict, training_bytes: int) -> str:
    rasterizer = sidecar["rasterizer"]
    return "\n".join(
        [
            "## Export",
            "",
            f"`artifacts/model/{sidecar['model_file']}` is the {sidecar['variant']} CNN saved without optimizer "
            f"state: {sidecar['file_bytes'] / 1024:,.0f} KB, against {training_bytes / 1024:,.0f} KB for the training "
            "save, which also holds Adam's two moment estimates for every weight. The export is reloaded before the "
            "sidecar is written and has to return six probabilities that sum to 1.",
            "",
            "`sidecar.json` sits next to it with what serving needs and what produced the file: labels in softmax "
            f"order, input size {sidecar['input']['size']} and `{sidecar['input']['polarity']}` polarity, the "
            f"rasterizer settings (canvas {rasterizer['raster_size']}, stroke width {rasterizer['stroke_width']}, pad "
            f"{rasterizer['pad_fraction']:.2f}), the gate (score at least {sidecar['gate']['min_score']:.2f}, margin "
            f"at least {sidecar['gate']['min_margin']:.2f}), {sidecar['parameter_count']:,} parameters, file size and "
            "SHA-256, validation and test metrics, and the git commit. Test metrics stay empty until "
            "`doodleverse.training.score_test_split` fills them in, once.",
        ]
    ) + "\n"


def export_model(
    model_dir: Path,
    gate_path: Path,
    manifest_path: Path,
    out_dir: Path,
    experiments_path: Path | None = None,
) -> dict:
    import tensorflow as tf

    report = json.loads((model_dir / "metrics.json").read_text(encoding="utf-8"))
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if gate["model_dir"] != model_dir.as_posix():
        raise ValueError(f"The gate in {gate_path} was chosen for {gate['model_dir']}, not {model_dir.as_posix()}.")
    sidecar_path = out_dir / SIDECAR_FILE
    if sidecar_path.exists() and json.loads(sidecar_path.read_text(encoding="utf-8")).get("test") is not None:
        raise RuntimeError(f"{out_dir} holds a test-scored export. Move it aside before exporting again.")
    manifest = read_manifest(manifest_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    model_path = out_dir / MODEL_FILE
    tf.keras.models.load_model(model_dir / "model.keras", compile=False).save(model_path)
    check_reload(model_path)
    sidecar = build_sidecar(model_path, report, gate, manifest_path, manifest)
    sidecar_path.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")
    if experiments_path is not None:
        upsert_section(experiments_path, "Export", export_section(sidecar, report["model_bytes"]), after="Stroke skew")
    return sidecar


def main() -> None:
    import argparse

    from doodleverse.training.select_cnn import kept_model_dir

    parser = argparse.ArgumentParser(description="Export the kept CNN with its sidecar.")
    parser.add_argument("--model-dir", type=Path, help="Defaults to the run kept by select_cnn.")
    parser.add_argument("--artifact-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--manifest", type=Path, default=Path("ml/splits/v1.json"))
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/model"))
    parser.add_argument("--experiments", type=Path, default=Path("docs/experiments.md"))
    args = parser.parse_args()
    sidecar = export_model(
        args.model_dir or kept_model_dir(args.artifact_dir),
        args.artifact_dir / "gate.json",
        args.manifest,
        args.out_dir,
        args.experiments,
    )
    print(
        f"wrote {args.out_dir / MODEL_FILE} ({sidecar['file_bytes'] / 1024:.0f} KB, sha256 {sidecar['sha256'][:12]}) "
        f"and {SIDECAR_FILE}"
    )


if __name__ == "__main__":
    main()
