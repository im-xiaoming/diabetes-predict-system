from __future__ import annotations

import os

import pendulum

from airflow import DAG
from airflow.operators.bash import BashOperator


PROJECT_DIR = os.environ.get("DIABETES_PROJECT_DIR", "/opt/diabetes_predict_system")
LOCAL_TZ = pendulum.timezone("Asia/Ho_Chi_Minh")

DEFAULT_ENV = {
    "PYTHONPATH": PROJECT_DIR,
    "PYTHONIOENCODING": "utf-8",
    "DJANGO_SETTINGS_MODULE": "diabetes_predict_system.settings",
    "MLFLOW_TRACKING_URI": f"sqlite:///{PROJECT_DIR}/mlflow.db",
    "MLFLOW_ARTIFACT_ROOT": f"file://{PROJECT_DIR}/mlruns",
    "MLFLOW_EXPERIMENT_NAME": "diabetes-complication-training-airflow",
}


with DAG(
    dag_id="retrain_diabetes_model",
    description="Run the DVC retraining pipeline and push updated DVC artifacts.",
    start_date=pendulum.datetime(2026, 5, 22, tz=LOCAL_TZ),
    # schedule="0 2 * * *",
    schedule="*/1 * * * *",
    catchup=False,
    max_active_runs=1,
    tags=["diabetes", "dvc", "retrain"],
) as dag:
    dvc_repro = BashOperator(
        task_id="dvc_repro",
        bash_command=(
            "set -euo pipefail; "
            f"cd {PROJECT_DIR}; "
            "dvc repro"
        ),
        env=DEFAULT_ENV,
        append_env=True,
        retries=1,
    )

    dvc_push = BashOperator(
        task_id="dvc_push",
        bash_command=(
            "set -euo pipefail; "
            f"cd {PROJECT_DIR}; "
            "if dvc remote default >/dev/null 2>&1; then "
            "dvc push; "
            "else "
            "echo 'No default DVC remote configured; skipping dvc push.'; "
            "fi"
        ),
        env=DEFAULT_ENV,
        append_env=True,
        retries=1,
    )

    dvc_repro >> dvc_push
