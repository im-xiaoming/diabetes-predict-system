# Airflow

Airflow nằm trong repository để version DAG và cấu hình orchestration cùng với Django code. Airflow không phải Django app và không được thêm vào `INSTALLED_APPS`.

## Vai trò

Trong project này, Airflow chỉ làm hai việc:

1. Chạy retrain pipeline theo lịch:

   ```bash
   dvc repro
   ```

2. Push artifact sau khi pipeline thành công:

   ```bash
   dvc push
   ```

Các bước nhỏ hơn như export dữ liệu, train model, so sánh candidate với champion, promote/reject model là trách nhiệm của `dvc.yaml` và `ml/train.py`, không phải của Airflow.

```text
Airflow
  -> dvc repro
      -> export_training_data
      -> train_model
      -> promotion gate
  -> dvc push
```

## DAG

DAG chính:

```text
retrain_diabetes_model
  -> check_retrain_policy
  -> dvc_repro
  -> dvc_push
  -> mark_retrain_success
```

File DAG:

```text
airflow/dags/retrain_diabetes_model.py
```

Lịch mặc định trong DAG được đọc từ file do Django admin quản lý:

```text
configs/airflow_retrain_config.json
```

Gia tri nay co the la cron (`0 2 * * *`), preset Airflow (`@daily`), `manual`/`none`, hoac interval nhu `15m`, `2h`, `1d`.

Không nên để lịch 1 phút cho pipeline retrain thật. Pipeline retrain có thể mất thời gian và `dvc.yaml` có stage export từ DB, nên nếu một lượt chạy chưa xong thì run mới sẽ bị giữ ở trạng thái `Queued` để chờ run trước chạy xong.

Khi cần demo, dùng nút Trigger trên Airflow UI hoặc tạm thời thêm `--force` vào task `check_retrain_policy`.

Khi muốn chỉ chạy thủ công trên UI, đổi lại:

```text
schedule=manual
```

Không dùng `pendulum.now()` hoặc giá trị thay đổi theo thời gian cho `start_date`, vì Airflow sẽ xem DAG thay đổi version sau mỗi lần parse.

## MLflow trong Airflow

Airflow chạy trong Linux container, còn khi train trực tiếp trên Windows thì MLflow có thể đã lưu artifact path dạng `C:\...` hoặc `file:///C:/...` trong `mlflow.db`. Path này không dùng được trong container và có thể gây lỗi:

```text
Permission denied: '/C:'
```

Vì vậy DAG truyền riêng các biến môi trường sau cho task:

```text
SQLITE_PATH=/opt/diabetes_predict_system/.runtime/db.sqlite3
MLFLOW_TRACKING_URI=postgresql+psycopg2://airflow:airflow@postgres/mlflow
MLFLOW_ARTIFACT_ROOT=file:///opt/diabetes_predict_system/mlruns
MLFLOW_EXPERIMENT_NAME=diabetes-complication-training-airflow
```

Experiment `diabetes-complication-training-airflow` dùng artifact path Linux bên trong container. Registry vẫn dùng cùng `mlflow.db`, nên model mới sau khi train thành công vẫn có thể được đăng ký và set alias `champion`.

## Docker image

Airflow dùng custom image trong `airflow/Dockerfile` để có dependency tối thiểu cho DVC pipeline. Base image dùng Python 3.11 để khớp môi trường đang train/load model của project:

- Django
- DVC
- MLflow
- pandas
- scikit-learn
- optuna

Các version trong Dockerfile nên khớp với môi trường API đang load `ml/artifacts/model.pkl`. Đặc biệt cần giữ cùng version `scikit-learn`, vì model được lưu bằng pickle/joblib có thể lỗi khi load bằng version khác.

Compose mount project root vào container:

```text
host:      ..
container: /opt/diabetes_predict_system
```

DAG chạy trong thư mục:

```text
DIABETES_PROJECT_DIR=/opt/diabetes_predict_system
```

## Chạy local

Từ project root:

```powershell
cd airflow
docker compose --env-file ../.env build
docker compose --env-file ../.env up airflow-init
docker compose --env-file ../.env up
```

Nếu Docker báo container name conflict do stack Airflow cũ còn tồn tại, dừng stack cũ trước:

```powershell
docker compose down
```

Airflow UI:

```text
http://localhost:8080
```

MLflow UI cho cac run do Airflow retrain tao:

```text
http://localhost:5001
```

Default local credentials:

```text
admin / 1
```

## DVC remote

Task `dvc_push` chỉ push artifact khi project đã có default DVC remote. Nếu chưa cấu hình remote, task sẽ ghi log và bỏ qua để DAG vẫn chạy được trong môi trường local dev.

Kiểm tra trong container:

```powershell
docker compose run --rm airflow-cli bash -lc "cd /opt/diabetes_predict_system && dvc remote list"
```

Nếu muốn lưu artifact lên remote thật, cấu hình DVC remote trước rồi chạy lại DAG.

## Runtime files

Các file runtime không commit:

- `airflow/logs/`
- `airflow/config/airflow.cfg`

## Retrain policy gate

DAG hien tai khong goi `dvc repro` truc tiep. Airflow chay:

```text
check_retrain_policy -> dvc_repro -> dvc_push -> mark_retrain_success
```

`check_retrain_policy` goi:

```bash
python ml/retrain_policy.py check
```

Neu chua du nguong du lieu moi, command exit code `99`; Airflow danh dau task la skipped va khong chay retrain. Neu du nguong, DAG tiep tuc `dvc_repro`, `dvc_push`, roi cap nhat state bang:

```bash
python ml/retrain_policy.py mark-success
```

Lich retrain doi trong Django admin:

```text
http://127.0.0.1:8000/admin/
Modeling -> Airflow retrain config
```

Admin config nay quan ly ca schedule, cac nguong retrain, va co `force` de ep retrain khi demo. Khi bam Save trong admin, Django ghi vao:

```text
configs/airflow_retrain_config.json
```

Schedule co the la cron (`0 2 * * *`), preset Airflow (`@daily`), `manual`/`none`, hoac interval nhu `15m`, `2h`, `1d`. Airflow va `ml/retrain_policy.py` doc file nay nen khong can build lai Docker.

Sieu tham so model va cau hinh Optuna doi trong Django admin:

```text
http://127.0.0.1:8000/admin/
Modeling -> Model training config
```

Admin ghi cau hinh nay vao:

```text
configs/model_training_config.json
```

`dvc repro` goi `ml/train.py --config configs/model_training_config.json`, nen co the doi `n_trials`, `timeout`, model families, promotion settings va search space ma khong can sua `dvc.yaml`.

Neu Airflow UI chua cap nhat ngay, restart Airflow scheduler/dag processor de DAG doc lai gia tri moi:

```powershell
cd airflow
docker compose --env-file ../.env restart airflow-scheduler airflow-dag-processor
```
