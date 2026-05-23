from __future__ import annotations

import os
import json
import re
import shlex
from datetime import timedelta
from pathlib import Path

import pendulum

from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator


PROJECT_DIR = os.environ.get("DIABETES_PROJECT_DIR", "/opt/diabetes_predict_system")
AIRFLOW_MLFLOW_TRACKING_URI = os.environ.get(
    "AIRFLOW_MLFLOW_TRACKING_URI",
    "postgresql+psycopg2://airflow:airflow@postgres/airflow",
)
AIRFLOW_MLFLOW_ARTIFACT_ROOT = os.environ.get(
    "AIRFLOW_MLFLOW_ARTIFACT_ROOT",
    f"file://{PROJECT_DIR}/mlruns",
)
RETRAIN_CONFIG_PATH = Path(
    os.environ.get(
        "AIRFLOW_RETRAIN_CONFIG_PATH",
        f"{PROJECT_DIR}/configs/airflow_retrain_config.json",
    )
)
LOCAL_TZ = pendulum.timezone("Asia/Ho_Chi_Minh")

DEFAULT_ENV = {
    "PYTHONPATH": PROJECT_DIR,
    "PYTHONUNBUFFERED": "1",
    "PYTHONIOENCODING": "utf-8",
    "DVC_NO_ANALYTICS": "1",
    "DJANGO_SETTINGS_MODULE": "diabetes_predict_system.settings",
    "SQLITE_PATH": f"{PROJECT_DIR}/.runtime/db.sqlite3",
    "MLFLOW_TRACKING_URI": AIRFLOW_MLFLOW_TRACKING_URI,
    "MLFLOW_ARTIFACT_ROOT": AIRFLOW_MLFLOW_ARTIFACT_ROOT,
    "MLFLOW_EXPERIMENT_NAME": "diabetes-complication-training-airflow",
}


def q(value):
    return shlex.quote(str(value))


def get_schedule_raw():
    if RETRAIN_CONFIG_PATH.exists():
        try:
            payload = json.loads(RETRAIN_CONFIG_PATH.read_text(encoding="utf-8"))
            schedule = str(payload.get("schedule", "")).strip()
            if schedule:
                return schedule
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    return os.environ.get("DIABETES_RETRAIN_SCHEDULE", "1d")


def parse_schedule(value):
    raw_value = (value or "").strip()
    lowered = raw_value.lower()
    if lowered in {"", "none", "manual", "manual_only", "off"}:
        return None

    match = re.fullmatch(
        r"(?P<amount>[1-9]\d*)\s*(?P<unit>m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days)",
        lowered,
    )
    if match:
        amount = int(match.group("amount"))
        unit = match.group("unit")
        if unit.startswith("m"):
            return timedelta(minutes=amount)
        if unit.startswith("h"):
            return timedelta(hours=amount)
        return timedelta(days=amount)

    return raw_value


RETRAIN_SCHEDULE_RAW = get_schedule_raw()
RETRAIN_SCHEDULE = parse_schedule(RETRAIN_SCHEDULE_RAW)


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
        bash_command=task_command("retrain_policy_check", "python -u ml/retrain_policy.py check"),
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
