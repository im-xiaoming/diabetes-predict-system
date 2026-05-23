#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="$ROOT_DIR/.runtime"
PID_DIR="$RUNTIME_DIR/pids"
LOG_DIR="$RUNTIME_DIR/logs"

DJANGO_PORT="${DJANGO_PORT:-8000}"
API_PORT="${API_PORT:-8001}"
MLFLOW_PORT="${MLFLOW_PORT:-5000}"

mkdir -p "$PID_DIR" "$LOG_DIR"
cd "$ROOT_DIR"

if [ -x "$ROOT_DIR/../venv/Scripts/python.exe" ]; then
  PYTHON="${PYTHON:-$ROOT_DIR/../venv/Scripts/python.exe}"
elif [ -x "$ROOT_DIR/../venv/bin/python" ]; then
  PYTHON="${PYTHON:-$ROOT_DIR/../venv/bin/python}"
else
  PYTHON="${PYTHON:-python}"
fi

export PYTHONUNBUFFERED=1
export DVC_NO_ANALYTICS="${DVC_NO_ANALYTICS:-1}"
export MLFLOW_TRACKING_URI="${MLFLOW_TRACKING_URI:-sqlite:///mlflow.db}"
export MLFLOW_ARTIFACT_ROOT="${MLFLOW_ARTIFACT_ROOT:-./mlruns}"

log() {
  printf '[run] %s\n' "$*"
}

warn() {
  printf '[run][warn] %s\n' "$*" >&2
}

run_optional() {
  local label="$1"
  shift

  log "$label"
  if ! "$@"; then
    warn "$label failed; continuing"
  fi
}

port_open() {
  "$PYTHON" - "$1" <<'PY'
import socket
import sys

port = int(sys.argv[1])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(0.5)
    sys.exit(0 if sock.connect_ex(("127.0.0.1", port)) == 0 else 1)
PY
}

start_service() {
  local name="$1"
  local port="$2"
  shift 2

  local pid_file="$PID_DIR/$name.pid"
  local log_file="$LOG_DIR/$name.log"

  if [ -f "$pid_file" ]; then
    local old_pid
    old_pid="$(cat "$pid_file" 2>/dev/null || true)"
    if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
      log "$name already running pid=$old_pid log=$log_file"
      return
    fi
  fi

  if [ -n "$port" ] && port_open "$port"; then
    log "$name already reachable on http://127.0.0.1:$port"
    return
  fi

  log "starting $name -> $log_file"
  if command -v nohup >/dev/null 2>&1; then
    nohup "$@" >"$log_file" 2>&1 &
  else
    "$@" >"$log_file" 2>&1 &
  fi
  echo "$!" > "$pid_file"
}

stop_service() {
  local pid_file="$1"
  local name
  name="$(basename "$pid_file" .pid)"

  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    log "stopping $name pid=$pid"
    kill "$pid" 2>/dev/null || true
  fi
  rm -f "$pid_file"
}

start_docker_stack() {
  if ! command -v docker >/dev/null 2>&1; then
    warn "Docker not found; skipping Airflow and Grafana"
    return
  fi

  run_optional "starting monitoring stack (Grafana/Prometheus)" \
    docker compose -f monitoring/docker-compose.yml up -d

  if [ ! -f airflow/.env ] && [ -f airflow/.env.example ]; then
    cp airflow/.env.example airflow/.env
  fi

  run_optional "building Airflow image" \
    docker compose -f airflow/docker-compose.yaml build
  run_optional "initializing Airflow metadata DB/user" \
    docker compose -f airflow/docker-compose.yaml up airflow-init
  run_optional "starting Airflow services" \
    docker compose -f airflow/docker-compose.yaml up -d airflow-apiserver airflow-scheduler airflow-worker airflow-triggerer airflow-dag-processor
}

start_all() {
  log "project: $ROOT_DIR"
  log "python: $PYTHON"

  run_optional "dvc pull" "$PYTHON" -m dvc pull -r origin
  log "applying Django migrations"
  "$PYTHON" manage.py migrate --noinput

  start_docker_stack

  start_service "api" "$API_PORT" \
    "$PYTHON" -m uvicorn api.main:app --host 127.0.0.1 --port "$API_PORT"

  start_service "django" "$DJANGO_PORT" \
    "$PYTHON" manage.py runserver "127.0.0.1:$DJANGO_PORT"

  start_service "mlflow" "$MLFLOW_PORT" \
    "$PYTHON" -m mlflow ui --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns --host 127.0.0.1 --port "$MLFLOW_PORT"

  log "ready"
  log "Django:  http://127.0.0.1:$DJANGO_PORT"
  log "API:     http://127.0.0.1:$API_PORT/docs"
  log "MLflow:  http://127.0.0.1:$MLFLOW_PORT"
  log "Airflow: http://127.0.0.1:8080"
  log "Grafana: http://127.0.0.1:3000"
  log "logs:    $LOG_DIR"
}

stop_all() {
  for pid_file in "$PID_DIR"/*.pid; do
    [ -e "$pid_file" ] || continue
    stop_service "$pid_file"
  done

  if command -v docker >/dev/null 2>&1; then
    run_optional "stopping monitoring stack" \
      docker compose -f monitoring/docker-compose.yml down
    run_optional "stopping Airflow stack" \
      docker compose -f airflow/docker-compose.yaml down
  fi
}

status_all() {
  for name in django api mlflow; do
    local pid_file="$PID_DIR/$name.pid"
    local pid=""
    [ -f "$pid_file" ] && pid="$(cat "$pid_file" 2>/dev/null || true)"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      log "$name running pid=$pid"
    else
      log "$name not running"
    fi
  done

  port_open "$DJANGO_PORT" && log "Django port $DJANGO_PORT open" || log "Django port $DJANGO_PORT closed"
  port_open "$API_PORT" && log "API port $API_PORT open" || log "API port $API_PORT closed"
  port_open "$MLFLOW_PORT" && log "MLflow port $MLFLOW_PORT open" || log "MLflow port $MLFLOW_PORT closed"
}

case "${1:-start}" in
  start)
    start_all
    ;;
  stop)
    stop_all
    ;;
  restart)
    stop_all
    start_all
    ;;
  status)
    status_all
    ;;
  *)
    echo "Usage: bash run.sh [start|stop|restart|status]"
    exit 2
    ;;
esac
