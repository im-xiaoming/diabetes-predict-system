# Quy trình DVC và retrain model

Trong project này, DB là nguồn dữ liệu vận hành, còn DVC quản lý các artifact có thể version:

- `data/data.csv`: seed dataset gốc.
- `data/training.csv`: dataset dùng để train, được export/merge từ DB và seed dataset.
- `ml/artifacts/model.pkl`: model đang được API sử dụng để predict.

## Luồng dữ liệu

```text
Mock HIS / HIS thật -> DB
ClinicalRecord + ClinicalRecordLabel -> data/training.csv
data/training.csv -> ml/train.py -> candidate model
candidate tốt hơn champion -> ml/artifacts/model.pkl + MLflow champion mới
candidate kém hơn champion -> giữ nguyên model.pkl và champion cũ
```

Không train bằng `RiskScoreDetail.risk_label` vì đây là output của model. Chỉ dùng ground-truth label trong `ClinicalRecordLabel`.

## Export dữ liệu train

Chạy export riêng:

```powershell
python ml/export_training_data.py --output data/training.csv --fallback data/data.csv
```

Stage export sẽ:

- đọc seed rows từ `data/data.csv`
- đọc labeled rows từ DB
- merge hai nguồn
- drop duplicate theo feature + label
- ghi ra `data/training.csv`

`export_training_data` được đặt `always_changed: true` trong `dvc.yaml` vì DB là runtime input, không nên commit hay track `db.sqlite3` trong DVC. Mỗi lần `dvc repro`, stage export sẽ chạy lại để lấy label mới từ DB.

## Train và promotion gate

Chạy train nhanh không tune:

```powershell
python ml/train.py --data data/training.csv
```

Chạy train có register MLflow và promotion gate:

```powershell
python ml/train.py --data data/training.csv --tune --n-trials 5 --timeout 600 --register --promotion-metric f1_macro --promotion-min-delta 0.0
```

Trong một lần retrain, `ml/train.py` vẫn chọn model tốt nhất của lần chạy đó theo `f1_macro`. Model này được gọi là candidate.

Candidate chỉ được promote nếu:

```text
candidate.f1_macro > champion.f1_macro + promotion_min_delta
```

Với cấu hình hiện tại:

```text
promotion_metric = f1_macro
promotion_min_delta = 0.0
```

Tức là candidate phải tốt hơn champion hiện tại. Nếu candidate kém hơn hoặc chỉ bằng champion, code sẽ:

- không ghi đè `ml/artifacts/model.pkl`
- không chuyển MLflow alias `champion`
- giữ nguyên model đang chạy trước đó

Nếu cần ép promote thủ công, dùng:

```powershell
python ml/train.py --data data/training.csv --register --force-promote
```

Chỉ dùng `--force-promote` khi đã kiểm tra kỹ metric và chấp nhận thay champion.

## Chạy pipeline DVC

```powershell
dvc repro
dvc push
```

Pipeline hiện có hai stage:

- `export_training_data`: tạo `data/training.csv`
- `train_model`: train candidate, kiểm tra promotion gate, rồi chỉ ghi `ml/artifacts/model.pkl` nếu candidate đạt điều kiện

Nếu candidate bị reject, `dvc repro` vẫn chạy thành công nhưng `ml/artifacts/model.pkl` không đổi.

Ngoại lệ vận hành: nếu candidate bị reject nhưng champion artifact cũ không thể restore/load trong môi trường hiện tại, ví dụ do lệch phiên bản scikit-learn khi unpickle, `train.py` sẽ promote candidate để API vẫn có `model.pkl` chạy được. Trường hợp này cần xem lại dependency trong `requirements.txt` để tránh model pickle bị lệch version giữa các lần train/deploy.

## Airflow

Airflow không định nghĩa lại từng bước export/train/promote. Các bước đó đã nằm trong `dvc.yaml` và `ml/train.py`.

Airflow chỉ lên lịch và chạy:

```text
dvc repro -> dvc push
```

DAG hiện tại:

```text
retrain_diabetes_model
  -> dvc_repro
  -> dvc_push
```

Nếu `dvc_repro` fail thì `dvc_push` không chạy. Nếu candidate model bị reject bởi promotion gate, `dvc_repro` vẫn thành công miễn là `ml/artifacts/model.pkl` được giữ hoặc restore hợp lệ.
