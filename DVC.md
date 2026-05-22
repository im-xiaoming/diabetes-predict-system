# Quy trình DVC

Trong project này, DB là nguồn dữ liệu vận hành, còn DVC quản lý các artifact có thể version:

- `data/data.csv`: seed dataset gốc.
- `data/training.csv`: dataset dùng để train, được export/merge từ DB và seed dataset.
- `ml/artifacts/model.pkl`: model artifact sau khi train.

Luồng retrain:

```text
Mock HIS / HIS thật -> DB
ClinicalRecord + ClinicalRecordLabel -> data/training.csv
data/training.csv -> ml/train.py -> ml/artifacts/model.pkl
```

Không train bằng `RiskScoreDetail.risk_label` vì đây là output của model. Chỉ dùng ground-truth label trong `ClinicalRecordLabel`.

Chạy export riêng:

```powershell
python ml/export_training_data.py --output data/training.csv --fallback data/data.csv
```

Chạy train nhanh không tune:

```powershell
python ml/train.py --data data/training.csv
```

Chạy pipeline DVC:

```powershell
dvc repro
dvc push
```

`export_training_data` được đặt `always_changed: true` vì DB là runtime input, không nên commit hay track `db.sqlite3` trong DVC. Mỗi lần `dvc repro`, stage export sẽ chạy lại và merge:

- seed rows từ `data/data.csv`
- labeled rows từ DB

Sau đó stage này drop duplicate theo feature + label để tạo `data/training.csv`.
