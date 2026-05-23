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

Database Django doc tu `.env`. Neu co `DATABASE_URL` thi uu tien bien do; neu khong, Django dung bo bien PostgreSQL:

```text
PGHOST=<postgres-host>
PGDATABASE=<database>
PGUSER=<user>
PGPASSWORD=<password>
PGPORT=5432
PGSSLMODE=require
```

Neu cac bien PostgreSQL de trong, app fallback ve SQLite tai `SQLITE_PATH`.

Neu muon MLflow log len DagsHub thay vi SQLite local, sua them:

```text
MLFLOW_TRACKING_URI=https://dagshub.com/<username>/<repo>.mlflow
MLFLOW_TRACKING_USERNAME=<dagshub-username>
MLFLOW_TRACKING_PASSWORD=<dagshub-token>
```

Neu giu mac dinh `sqlite:////app/runtime/mlflow.db`, MLflow se chay local trong thu muc `.runtime/` cua project.

Mac dinh `.env` hien bat:

```text
RESET_DATABASE_ON_START=False
DJANGO_CREATE_SUPERUSER=True
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_PASSWORD=1
```

Voi DB cloud/PostgreSQL, `RESET_DATABASE_ON_START` nen de `False`; entrypoint cung se bo qua reset khi phat hien `DATABASE_URL` hoac `PGHOST`. Khi start container, Django van migrate va tao/cap nhat tai khoan admin.

## Airflow

Airflow dang co compose rieng trong thu muc `airflow/`, vi stack nay lon va dung image rieng. Airflow khong dung `airflow/.env` rieng nua; no doc cau hinh tu `.env` o thu muc root.

```bash
cd airflow
docker compose --env-file ../.env up --build
```

Airflow UI: http://127.0.0.1:8080

Airflow login local:

```text
admin / 1
```

Schedule va cac nguong retrain duoc doi trong Django admin:

```text
http://127.0.0.1:8000/admin/
Modeling -> Airflow retrain config
```

Gia tri schedule co the la cron (`0 2 * * *`), preset Airflow (`@daily`), `manual`/`none`, hoac interval nhu `15m`, `2h`, `1d`. Cac nguong policy va `force` cung nam o form nay. Khi bam Save trong admin, Django ghi vao `configs/airflow_retrain_config.json`; Airflow va `ml/retrain_policy.py` doc file nay nen khong can build lai Docker. Neu Airflow UI chua cap nhat ngay, restart scheduler va dag processor:

```bash
cd airflow
docker compose --env-file ../.env restart airflow-scheduler airflow-dag-processor
```
