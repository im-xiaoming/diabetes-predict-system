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
  -> dvc_repro
  -> dvc_push
```

File DAG:

```text
airflow/dags/retrain_diabetes_model.py
```

Lịch test hiện tại trong môi trường dev:

```text
Chạy mỗi 1 phút.
```

Trong file DAG đang để:

```python
schedule="*/1 * * * *"
```

Lịch 1 phút chỉ nên dùng để test. Pipeline retrain có thể mất thời gian và `dvc.yaml` có stage export được đánh dấu `always_changed`, nên Airflow sẽ chạy lại pipeline liên tục. Khi `max_active_runs=1`, nếu một lượt chạy chưa xong thì run mới sẽ bị giữ ở trạng thái `Queued` để chờ run trước chạy xong.

Khi muốn chỉ chạy thủ công trên UI, đổi lại:

```python
schedule=None
```

Khi cần chạy theo lịch thật, đổi `schedule` trong DAG, ví dụ 02:00 mỗi ngày theo timezone `Asia/Ho_Chi_Minh`:

```python
schedule="0 2 * * *"
```

Không dùng `pendulum.now()` hoặc giá trị thay đổi theo thời gian cho `start_date`, vì Airflow sẽ xem DAG thay đổi version sau mỗi lần parse.

## MLflow trong Airflow

Airflow chạy trong Linux container, còn khi train trực tiếp trên Windows thì MLflow có thể đã lưu artifact path dạng `C:\...` hoặc `file:///C:/...` trong `mlflow.db`. Path này không dùng được trong container và có thể gây lỗi:

```text
Permission denied: '/C:'
```

Vì vậy DAG truyền riêng các biến môi trường sau cho task:

```text
MLFLOW_TRACKING_URI=sqlite:////opt/diabetes_predict_system/mlflow.db
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
Copy-Item .env.example .env
docker compose build
docker compose up airflow-init
docker compose up
```

Nếu Docker báo container name conflict do stack Airflow cũ còn tồn tại, dừng stack cũ trước:

```powershell
docker compose down
```

Airflow UI:

```text
http://localhost:8080
```

Default local credentials:

```text
airflow / airflow
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
- `airflow/.env`
