Trong project này, DVC nên quản lý:

- `data/data.csv`
- `ml/artifacts/model.pkl`
- có thể thêm `mlruns/` artifact quan trọng nếu muốn, nhưng thường MLflow đã quản lý experiment rồi nên không nhất thiết đưa toàn bộ `mlruns` vào DVC.

Luồng hợp lý:

```text
Git: code, config, pipeline definition
DVC: dataset, model artifact
MLflow: experiment tracking, metrics, registry
Airflow/Cron: lịch retrain định kỳ
Django: UI thao tác thủ công/xem trạng thái
```

Thứ tự nên làm:

1. Cài và init DVC:
   ```bash
   pip install dvc
   dvc init
   ```

2. Track dataset:
   ```bash
   dvc add data/data.csv
   git add data/data.csv.dvc .gitignore
   git commit -m "Track dataset with DVC"
   ```

3. Track model artifact:
   ```bash
   dvc add ml/artifacts/model.pkl
   git add ml/artifacts/model.pkl.dvc .gitignore
   git commit -m "Track trained model artifact with DVC"
   ```

4. Cấu hình remote DVC:
   ```bash
   ...
   dvc push -r origin
   ```

Bước “chuẩn” hơn nữa là tạo `dvc.yaml` để pipeline có thể reproduce:

```bash
dvc stage add -n train_model \
  -d data/data.csv \
  -d ml/train.py \
  -o ml/artifacts/model.pkl \
  python ml/train.py --tune --n-trials 5 --timeout 600 --register

dvc repro

dvc push -r origin
```

Tóm lại: **đúng, DVC là bước tiếp theo nếu bạn muốn version data/model**. Sau DVC mới tính tiếp scheduler như Airflow để tự động chạy lại pipeline.