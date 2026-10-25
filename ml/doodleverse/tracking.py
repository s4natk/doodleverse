from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


def sqlite_tracking_uri(directory: Path) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    database = (directory / "mlflow.db").resolve()
    return "sqlite:///" + database.as_posix()


def _experiment_id(client, directory: Path, name: str) -> str:
    found = client.get_experiment_by_name(name)
    if found is not None:
        return found.experiment_id
    # Keep logged files under the tracking directory instead of the working directory.
    artifact_root = (directory / "artifacts" / name).resolve().as_uri()
    return client.create_experiment(name, artifact_location=artifact_root)


def log_run(
    tracking_dir: Path,
    experiment: str,
    run_name: str,
    params: dict,
    metrics: dict,
    artifacts: Iterable[Path] = (),
) -> str:
    import mlflow
    from mlflow.tracking import MlflowClient

    uri = sqlite_tracking_uri(tracking_dir)
    mlflow.set_tracking_uri(uri)
    experiment_id = _experiment_id(MlflowClient(uri), tracking_dir, experiment)
    with mlflow.start_run(experiment_id=experiment_id, run_name=run_name) as run:
        mlflow.log_params({key: value for key, value in params.items() if isinstance(value, (str, int, float))})
        mlflow.log_metrics({key: float(value) for key, value in metrics.items()})
        for path in artifacts:
            mlflow.log_artifact(str(path))
        return run.info.run_id
