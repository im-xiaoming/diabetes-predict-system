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

reset_database() {
  if is_true "${RESET_DATABASE_ON_START:-False}"; then
    if [ -n "${DATABASE_URL:-}" ] || [ -n "${PGHOST:-}" ]; then
      echo "[entrypoint] RESET_DATABASE_ON_START ignored for PostgreSQL/cloud database"
      return 0
    fi
    echo "[entrypoint] resetting SQLite database files"
    python - <<'PY'
import os
from pathlib import Path

targets = [
    os.environ.get("SQLITE_PATH"),
]

seen = set()
for raw_path in targets:
    if not raw_path:
        continue
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.resolve()
    if str(path) in seen or str(path) in {"/", str(Path.cwd())}:
        continue
    seen.add(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    for candidate in (path, Path(f"{path}-journal"), Path(f"{path}-wal"), Path(f"{path}-shm")):
        if candidate.exists() and candidate.is_file():
            candidate.unlink()
            print(f"[entrypoint] removed {candidate}")
PY
  fi
}

run_migrations() {
  if is_true "${RUN_MIGRATIONS:-True}"; then
    echo "[entrypoint] python manage.py migrate --noinput"
    python manage.py migrate --noinput
  fi
}

create_superuser() {
  if is_true "${DJANGO_CREATE_SUPERUSER:-False}"; then
    echo "[entrypoint] creating/updating Django superuser ${DJANGO_SUPERUSER_USERNAME:-admin}"
    python manage.py shell <<'PY'
import os
from django.contrib.auth import get_user_model


User = get_user_model()
username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "1")
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com")

user, _ = User.objects.get_or_create(username=username)
user.email = email
user.is_active = True
user.is_staff = True
user.is_superuser = True
user.set_password(password)
user.save()
print(f"[entrypoint] Django superuser ready: {username}")
PY
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
    reset_database
    run_migrations
    create_superuser
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
