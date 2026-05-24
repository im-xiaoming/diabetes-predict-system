# Docker

## Chạy app chính

```bash
cd C:\diabetes\diabetes_predict_system
docker compose up --build
```

UI:

- Django: http://127.0.0.1:8000
- FastAPI docs: http://127.0.0.1:8001/docs
- MLflow local app stack: http://127.0.0.1:5000
- Prometheus: http://127.0.0.1:9090
- Grafana: http://127.0.0.1:3000

Grafana login local:

```text
admin / admin
```

## Lệnh quản lý

```bash
docker compose ps
docker compose logs -f django
docker compose logs -f api
docker compose down
```

Docker Compose tự đọc file `.env` trong thư mục project. Nếu muốn container tự pull artifact DVC khi start, sửa:

```text
DVC_PULL=True
DVC_REMOTE=origin
AWS_ACCESS_KEY_ID=<dagshub-access-key>
AWS_SECRET_ACCESS_KEY=<dagshub-secret-key>
```

Remote DVC `origin` đang trỏ tới DagsHub trong `.dvc/config`. Không đưa `.dvc/config.local` vào Docker image; file đó chỉ nên nằm trên máy local. Container sẽ lấy credential từ `.env` qua biến môi trường `AWS_ACCESS_KEY_ID` và `AWS_SECRET_ACCESS_KEY`.

Database Django đọc từ `.env`. Nếu có `DATABASE_URL` thì ưu tiên biến đó; nếu không, Django dùng bộ biến PostgreSQL:

```text
PGHOST=<postgres-host>
PGDATABASE=<database>
PGUSER=<user>
PGPASSWORD=<password>
PGPORT=5432
PGSSLMODE=require
```

Nếu các biến PostgreSQL để trống, app fallback về SQLite tại `SQLITE_PATH`.

Nếu muốn MLflow log lên DagsHub thay vì SQLite local, sửa thêm:

```text
MLFLOW_TRACKING_URI=https://dagshub.com/<username>/<repo>.mlflow
MLFLOW_TRACKING_USERNAME=<dagshub-username>
MLFLOW_TRACKING_PASSWORD=<dagshub-token>
```

Nếu giữ mặc định `sqlite:////app/runtime/mlflow.db`, MLflow sẽ chạy local trong thư mục `.runtime/` của project.

Mặc định `.env` hiện bật:

```text
RESET_DATABASE_ON_START=False
DJANGO_CREATE_SUPERUSER=True
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_PASSWORD=1
```

Với DB cloud/PostgreSQL, `RESET_DATABASE_ON_START` nên để `False`; entrypoint cũng sẽ bỏ qua reset khi phát hiện `DATABASE_URL` hoặc `PGHOST`. Khi start container, Django vẫn migrate và tạo/cập nhật tài khoản admin.

## Airflow

Airflow đang có compose riêng trong thư mục `airflow/`, vì stack này lớn và dùng image riêng. Airflow không dùng `airflow/.env` riêng nữa; nó đọc cấu hình từ `.env` ở thư mục root.

```bash
cd airflow
# docker compose --env-file ../.env down -v
docker compose --env-file ../.env up --build
```

Airflow UI: http://127.0.0.1:8080

MLflow UI cho các run do Airflow retrain tạo: http://127.0.0.1:5001

Airflow login local:

```text
admin / 1
```

Schedule và các ngưỡng retrain được đổi trong Django admin:

```text
http://127.0.0.1:8000/admin/
Modeling -> Airflow retrain config
```

Giá trị schedule có thể là cron (`0 2 * * *`), preset Airflow (`@daily`), `manual`/`none`, hoặc interval như `15m`, `2h`, `1d`. Các ngưỡng policy và `force` cũng nằm ở form này. Khi bấm Save trong admin, Django ghi vào `configs/airflow_retrain_config.json`; Airflow và `ml/retrain_policy.py` đọc file này nên không cần build lại Docker. Nếu Airflow UI chưa cập nhật ngay, restart scheduler và dag processor:

Siêu tham số model và cấu hình Optuna cũng đổi trong Django admin:

```text
http://127.0.0.1:8000/admin/
Modeling -> Model training config
```

Form này quản lý `n_trials`, `timeout`, model được train, promotion metric, có log Optuna trial hay không, và JSON search space cho từng model. Khi bấm Save, Django ghi vào `configs/model_training_config.json`; `dvc repro`/`ml/train.py` đọc file này nên không cần sửa `dvc.yaml`.

```bash
cd airflow
docker compose --env-file ../.env restart airflow-scheduler airflow-dag-processor
```
