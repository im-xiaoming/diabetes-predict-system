import json
import os
import tempfile
from pathlib import Path

import joblib
import mlflow
from mlflow.tracking import MlflowClient


ROOT_DIR = Path(__file__).resolve().parent.parent
MLRUNS_DIR = ROOT_DIR / "mlruns"
DEFAULT_EXP_NAME = "diabetes-complication-training"


def _artifact_root_uri():
    artifact_root = os.environ.get("MLFLOW_ARTIFACT_ROOT")
    if artifact_root:
        return artifact_root
    return MLRUNS_DIR.resolve().as_uri()


def _experiment_name():
    return os.environ.get("MLFLOW_EXPERIMENT_NAME", DEFAULT_EXP_NAME)


def setup_tracking():
    MLRUNS_DIR.mkdir(parents=True, exist_ok=True)

    db_path = ROOT_DIR / "mlflow.db"
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", f"sqlite:///{db_path.resolve().as_posix()}")
    artifact_uri = _artifact_root_uri()
    experiment_name = _experiment_name()

    mlflow.set_tracking_uri(tracking_uri)

    client = MlflowClient()
    exp = mlflow.get_experiment_by_name(experiment_name)
    if exp is None:
        mlflow.create_experiment(
            name=experiment_name,
            artifact_location=artifact_uri
        )
    elif getattr(exp, "lifecycle_stage", None) == "deleted":
        client.restore_experiment(exp.experiment_id)

    mlflow.set_experiment(experiment_name)

    return tracking_uri


def start_run(name):
    setup_tracking()
    return mlflow.start_run(run_name=name)


def log_params(params):
    out = {}
    for k, v in params.items():
        if isinstance(v, (list, tuple, dict)):
            out[k] = json.dumps(v, ensure_ascii=False)
        else:
            out[k] = v
    mlflow.log_params(out)


def log_metrics(metrics):
    out = {k: float(v) for k, v in metrics.items()}
    mlflow.log_metrics(out)


def log_report(txt, js):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)
        txt_path = path / "classification_report.txt"
        js_path = path / "classification_report.json"
        txt_path.write_text(txt, encoding="utf-8")
        js_path.write_text(json.dumps(js, ensure_ascii=False, indent=2), encoding="utf-8")
        mlflow.log_artifact(str(txt_path))
        mlflow.log_artifact(str(js_path))


def log_model(mdl):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "model.pkl"
        joblib.dump(mdl, path)
        mlflow.log_artifact(str(path), artifact_path="model")
