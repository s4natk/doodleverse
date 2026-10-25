from mlflow.tracking import MlflowClient

from doodleverse.tracking import log_run, sqlite_tracking_uri


def test_mlflow_records_metrics_and_artifacts_under_the_tracking_dir(tmp_path):
    directory = tmp_path / "mlflow"
    figure = tmp_path / "confusion_val.png"
    figure.write_bytes(b"png")
    run_id = log_run(
        directory,
        "doodleverse-baseline",
        "toy",
        {"C": 0.1, "solver": "lbfgs"},
        {"val_accuracy": 0.5, "val_macro_f1": 0.4},
        [figure],
    )
    client = MlflowClient(sqlite_tracking_uri(directory))
    stored = client.get_run(run_id)
    assert stored.data.metrics["val_macro_f1"] == 0.4
    assert stored.data.params["solver"] == "lbfgs"
    assert [item.path for item in client.list_artifacts(run_id)] == ["confusion_val.png"]
    assert any((directory / "artifacts").rglob("confusion_val.png"))
