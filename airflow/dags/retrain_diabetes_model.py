from __future__ import annotations

import os

import pendulum

from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator


PROJECT_DIR = os.environ.get("DIABETES_PROJECT_DIR", "/opt/diabetes_predict_system")
LOCAL_TZ = pendulum.timezone("Asia/Ho_Chi_Minh")

DEFAULT_ENV = {
    "PYTHONPATH": PROJECT_DIR,
    "PYTHONUNBUFFERED": "1",
    "PYTHONIOENCODING": "utf-8",
    "DVC_NO_ANALYTICS": "1",
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
            "set -euo pipefail\n"
            f"cd {PROJECT_DIR}\n"
            "echo \"[airflow] $(date -Is) dvc_repro_start project_dir=$(pwd)\"\n"
            "echo \"[airflow] $(date -Is) dvc_status_before\"\n"
            "dvc status || true\n"
            "dvc repro\n"
            "echo \"[airflow] $(date -Is) dvc_repro_done\"\n"
        ),
        env=DEFAULT_ENV,
        append_env=True,
        retries=1,
    )

    dvc_push = BashOperator(
        task_id="dvc_push",
        bash_command=(
            "set -euo pipefail\n"
            f"cd {PROJECT_DIR}\n"
            "echo \"[airflow] $(date -Is) dvc_push_start project_dir=$(pwd)\"\n"
            "if dvc remote default >/dev/null 2>&1; then\n"
            "  dvc push\n"
            "  echo \"[airflow] $(date -Is) dvc_push_done\"\n"
            "else\n"
            "  echo \"[airflow] $(date -Is) dvc_push_skipped reason=no_default_remote\"\n"
            "fi\n"
        ),
        env=DEFAULT_ENV,
        append_env=True,
        retries=1,
    )

    dvc_repro >> dvc_push
