import subprocess
import sys

# The serve extra does not install these. Importing any of them on the serving path is a bug.
TRAINING_ONLY = ("matplotlib", "sklearn", "mlflow", "joblib")


def test_serving_runs_without_the_training_dependencies(model_dir):
    script = "\n".join(
        [
            "import sys",
            "from pathlib import Path",
            f"for name in {TRAINING_ONLY!r}:",
            "    sys.modules[name] = None",
            "from fastapi.testclient import TestClient",
            "from doodleverse_api.main import create_app",
            "from doodleverse_api.settings import Settings",
            "with TestClient(create_app(Settings(model_dir=Path(sys.argv[1])))) as client:",
            "    body = {'canvas': {'width': 64, 'height': 64}, 'strokes': [[[1, 1], [40, 30]]]}",
            "    assert client.post('/predict', json=body).status_code == 200",
            f"print(sorted(name for name in {TRAINING_ONLY!r} if sys.modules.get(name) is not None))",
        ]
    )
    completed = subprocess.run(
        [sys.executable, "-c", script, str(model_dir)],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert completed.returncode == 0, completed.stderr[-3000:]
    assert completed.stdout.strip().splitlines()[-1] == "[]"
