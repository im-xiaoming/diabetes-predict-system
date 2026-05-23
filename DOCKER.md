# Docker

## Chay app chinh

```bash
cd C:\diabetes\diabetes_predict_system
docker compose up --build
```

UI:

- Django: http://127.0.0.1:8000
- FastAPI docs: http://127.0.0.1:8001/docs
- MLflow: http://127.0.0.1:5000
- Prometheus: http://127.0.0.1:9090
- Grafana: http://127.0.0.1:3000

Grafana login local:

```text
admin / admin
```

## Lenh quan ly

```bash
docker compose ps
docker compose logs -f django
docker compose logs -f api
docker compose down
```

Docker Compose tu doc file `.env` trong thu muc project. Neu muon container tu pull artifact DVC khi start, sua:

```text
DVC_PULL=True
DVC_REMOTE=origin
```

## Airflow

Airflow dang co compose rieng trong thu muc `airflow/`, vi stack nay lon va dung image rieng:

```bash
cd airflow
docker compose up --build
```

Airflow UI: http://127.0.0.1:8080
