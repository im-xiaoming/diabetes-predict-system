from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import tempfile

import joblib
import mlflow
from mlflow.tracking import MlflowClient

from ml.tracking import setup_tracking


REGISTERED_MODEL = "diabetes-complication-best"


def register_best_model(model, model_name, metrics, params, alias="champion"):
    setup_tracking()
    client = MlflowClient()
    with mlflow.start_run(run_name=f"register_{model_name}") as run:
        mlflow.log_params({k: v for k, v in params.items() if not isinstance(v, (list, dict, tuple))})
        mlflow.log_metrics({k: float(v) for k, v in metrics.items()})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.pkl"
            joblib.dump(model, path)
            mlflow.log_artifact(str(path), artifact_path="model")
        run_id = run.info.run_id
        model_uri = f"runs:/{run_id}/model"

    try:
        client.create_registered_model(REGISTERED_MODEL)
    except Exception:
        pass

    mv = client.create_model_version(
        name=REGISTERED_MODEL,
        source=model_uri,
        run_id=run_id,
    )
    try:
        client.set_registered_model_alias(REGISTERED_MODEL, alias, mv.version)
    except Exception:
        pass
    client.set_model_version_tag(REGISTERED_MODEL, mv.version, "model_family", model_name)
    for k, v in metrics.items():
        client.set_model_version_tag(REGISTERED_MODEL, mv.version, f"metric.{k}", f"{float(v):.6f}")
    return {
        "name": REGISTERED_MODEL,
        "version": mv.version,
        "run_id": run_id,
        "alias": alias,
    }


def load_champion():
    setup_tracking()
    client = MlflowClient()
    mv = client.get_model_version_by_alias(REGISTERED_MODEL, "champion")
    local_dir = client.download_artifacts(mv.run_id, "model")
    model_path = Path(local_dir) / "model.pkl"
    return joblib.load(model_path), mv
