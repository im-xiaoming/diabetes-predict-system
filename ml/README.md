# MLflow

## Chạy MLflow UI

Chạy từ thư mục gốc project:

```powershell
cd C:\diabetes\diabetes_predict_system
$env:MLFLOW_TRACKING_URI="sqlite:///mlflow.db"
mlflow ui --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns
```

Sau đó mở:

```text
http://localhost:5000
```

Không chạy lệnh ngắn:

```powershell
mlflow ui
```

Lệnh ngắn này làm MLflow đọc `./mlruns` như FileStore. Trong project này `mlruns` đang được dùng chủ yếu làm artifact root cho SQLite tracking store `mlflow.db`, nên một số thư mục run không có `meta.yaml`. Khi đó MLflow có thể báo:

```text
Malformed experiment ... meta.yaml does not exist
```

Đây là cảnh báo do chạy UI sai backend, không phải lỗi Airflow hay lỗi train model.

## Train thủ công

```powershell
python .\ml\train.py --tune --n-trials 5 --timeout 600 --register
```

Khi dùng `--tune`, Optuna sẽ thử nhiều bộ hyperparameter. Mặc định mỗi model family được gom thành một parent run trong MLflow:

```text
optuna_logistic_regression
  trial_0
  trial_1

optuna_random_forest
  trial_0
  trial_1
```

Parent run có:

```text
tags.run_type=optuna_study
tags.model_family=<model_name>
metrics.best_cv_f1_macro=<điểm tốt nhất>
params.best_<hyperparameter>=<giá trị tốt nhất>
```

Mỗi child trial run có:

```text
tags.run_type=optuna_trial
tags.model_family=<model_name>
metrics.cv_f1_macro=<điểm cross-validation>
params.<hyperparameter>=<giá trị thử>
```

Để xem gọn trong MLflow UI, có thể filter chỉ hiện parent run:

```text
tags.run_type = 'optuna_study'
```

Khi cần xem từng trial, mở parent run hoặc bỏ filter và xem các run `trial_*` có tag `mlflow.parentRunId`.

Sau các trial, training vẫn tạo run tổng hợp cho model tốt nhất của từng family, ví dụ `logistic_regression`, `random_forest`, rồi mới tạo `register_*` nếu model được đăng ký.

Nếu không muốn log từng trial:

```powershell
python .\ml\train.py --tune --n-trials 5 --timeout 600 --register --no-log-optuna-trials
```

Code training tự gọi `ml.tracking.setup_tracking()`, mặc định dùng:

```text
tracking store: sqlite:///mlflow.db
artifact root:  ./mlruns
experiment:     diabetes-complication-training
```

Nếu experiment bị xóa mềm trong MLflow UI, `setup_tracking()` sẽ tự restore lại experiment đó trước khi train.

## Airflow

Airflow chạy trong Linux container nên DAG truyền riêng:

```text
MLFLOW_TRACKING_URI=sqlite:////opt/diabetes_predict_system/mlflow.db
MLFLOW_ARTIFACT_ROOT=file:///opt/diabetes_predict_system/mlruns
MLFLOW_EXPERIMENT_NAME=diabetes-complication-training-airflow
```

Vì vậy nếu xem experiment do Airflow tạo từ MLflow UI chạy trên Windows, một số artifact path có thể là đường dẫn Linux `/opt/diabetes_predict_system/...`. Tracking metadata vẫn nằm trong cùng `mlflow.db`.
