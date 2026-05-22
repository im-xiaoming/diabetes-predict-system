# Monitoring

This stack keeps API operations metrics and prediction data separate:

- Prometheus scrapes FastAPI metrics from `http://host.docker.internal:8001/metrics`.
- Grafana reads Prometheus for service metrics.
- Grafana reads the local Django SQLite database for prediction, risk, and request log panels.

Run Django migrations before starting Grafana so `db.sqlite3` exists:

```powershell
python manage.py migrate
python -m uvicorn api.main:app --port 8001
docker compose -f monitoring/docker-compose.yml up -d
```

Open:

- Grafana: `http://127.0.0.1:3000`
- Prometheus: `http://127.0.0.1:9090`
- FastAPI metrics: `http://127.0.0.1:8001/metrics`

Grafana login for the local stack:

```text
username: admin
password: admin
```

The dashboard uses `db.sqlite3` as a read-only development data source. A larger deployment should move Django persistence to PostgreSQL or another managed relational database before exposing SQL dashboards.
