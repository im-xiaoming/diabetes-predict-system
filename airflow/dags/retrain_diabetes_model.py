from __future__ import annotations

import os
import shlex

import pendulum

from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator


PROJECT_DIR = os.environ.get("DIABETES_PROJECT_DIR", "/opt/diabetes_predict_system")
RETRAIN_SCHEDULE = os.environ.get("DIABETES_RETRAIN_SCHEDULE", "0 2 * * *")
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


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def q(value):
    return shlex.quote(str(value))


FORCE_RETRAIN = env_bool("DIABETES_RETRAIN_FORCE", False)
FORCE_ARG = " --force" if FORCE_RETRAIN else ""


def task_command(name, body):
    return (
        "set -euo pipefail\n"
        f"cd {q(PROJECT_DIR)}\n"
        f"echo \"[airflow] $(date -Is) {name}_start project_dir=$(pwd)\"\n"
        f"{body}\n"
        f"echo \"[airflow] $(date -Is) {name}_done\"\n"
    )


with DAG(
    dag_id="retrain_diabetes_model",
    description="Run the DVC retraining pipeline and push updated DVC artifacts.",
    start_date=pendulum.datetime(2026, 5, 22, tz=LOCAL_TZ),
    schedule=RETRAIN_SCHEDULE,
    catchup=False,
    max_active_runs=1,
    tags=["diabetes", "dvc", "retrain"],
) as dag:
    check_retrain_policy = BashOperator(
        task_id="check_retrain_policy",
        bash_command=task_command("retrain_policy_check", f"python -u ml/retrain_policy.py check{FORCE_ARG}"),
        env=DEFAULT_ENV,
        append_env=True,
        retries=0,
        skip_on_exit_code=99,
    )

    dvc_repro = BashOperator(
        task_id="dvc_repro",
        bash_command=task_command(
            "dvc_repro",
            "echo \"[airflow] $(date -Is) dvc_status_before\"\n"
            "dvc status || true\n"
            "dvc repro",
        ),
        env=DEFAULT_ENV,
        append_env=True,
        retries=1,
    )

    mark_retrain_success = BashOperator(
        task_id="mark_retrain_success",
        bash_command=task_command("mark_retrain_success", "python -u ml/retrain_policy.py mark-success"),
        env=DEFAULT_ENV,
        append_env=True,
        retries=0,
    )

    dvc_push = BashOperator(
        task_id="dvc_push",
        bash_command=task_command(
            "dvc_push",
            "if dvc remote default >/dev/null 2>&1; then\n"
            "  dvc push\n"
            "else\n"
            "  echo \"[airflow] $(date -Is) dvc_push_skipped reason=no_default_remote\"\n"
            "fi",
        ),
        env=DEFAULT_ENV,
        append_env=True,
        retries=1,
    )

    check_retrain_policy >> dvc_repro >> dvc_push >> mark_retrain_success
