#!/usr/bin/env sh
set -eu

cd /app

is_true() {
  case "$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')" in
    1|true|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

run_dvc_pull() {
  if is_true "${DVC_PULL:-False}"; then
    remote="${DVC_REMOTE:-origin}"
    echo "[entrypoint] dvc pull -r ${remote}"
    python -m dvc pull -r "${remote}" || echo "[entrypoint][warn] dvc pull failed; continuing"
  fi
}

run_migrations() {
  if is_true "${RUN_MIGRATIONS:-True}"; then
    echo "[entrypoint] python manage.py migrate --noinput"
    python manage.py migrate --noinput
  fi
}

run_collectstatic() {
  if is_true "${RUN_COLLECTSTATIC:-False}"; then
    echo "[entrypoint] python manage.py collectstatic --noinput"
    python manage.py collectstatic --noinput
  fi
}

case "${1:-django}" in
  django)
    run_dvc_pull
    run_migrations
    run_collectstatic
    exec python manage.py runserver "0.0.0.0:${DJANGO_PORT:-8000}"
    ;;
  api)
    run_dvc_pull
    exec python -m uvicorn api.main:app --host 0.0.0.0 --port "${API_PORT:-8001}"
    ;;
  mlflow)
    exec python -m mlflow ui \
      --backend-store-uri "${MLFLOW_TRACKING_URI:-sqlite:////app/runtime/mlflow.db}" \
      --default-artifact-root "${MLFLOW_ARTIFACT_ROOT:-/app/mlruns}" \
      --host 0.0.0.0 \
      --port "${MLFLOW_PORT:-5000}"
    ;;
  train)
    shift
    run_dvc_pull
    exec python -u ml/train.py "$@"
    ;;
  *)
    exec "$@"
    ;;
esac
