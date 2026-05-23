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
AWS_ACCESS_KEY_ID=<dagshub-access-key>
AWS_SECRET_ACCESS_KEY=<dagshub-secret-key>
```

Remote DVC `origin` dang tro toi DagsHub trong `.dvc/config`. Khong dua `.dvc/config.local` vao Docker image; file do chi nen nam tren may local. Container se lay credential tu `.env` qua bien moi truong `AWS_ACCESS_KEY_ID` va `AWS_SECRET_ACCESS_KEY`.

Neu muon MLflow log len DagsHub thay vi SQLite local, sua them:

```text
MLFLOW_TRACKING_URI=https://dagshub.com/<username>/<repo>.mlflow
MLFLOW_TRACKING_USERNAME=<dagshub-username>
MLFLOW_TRACKING_PASSWORD=<dagshub-token>
```

Neu giu mac dinh `sqlite:////app/runtime/mlflow.db`, MLflow se chay local trong Docker volume.

## Airflow

Airflow dang co compose rieng trong thu muc `airflow/`, vi stack nay lon va dung image rieng:

```bash
cd airflow
docker compose up --build
```

Airflow UI: http://127.0.0.1:8080
