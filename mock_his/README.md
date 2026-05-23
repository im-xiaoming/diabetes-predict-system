# Mock HIS

App `mock_his` dung de gia lap HIS (*Hospital Information System*).

Day khong phai app nghiep vu chinh, ma la app demo/test luong du lieu benh vien gui ho so benh nhan sang he thong du doan bien chung tieu duong.

## Chuc nang

- Sinh du lieu benh nhan mock ngau nhien qua `mock_his/sample_loader.py`.
- Moi record mock co `patient_id`, feature va label rieng de tranh trung voi seed dataset `data/data.csv` khi export ra `data/training.csv`.
- Hien thi giao dien mo phong tai `/mock-his/`.
- Gui tung ho so hoac gui hang loat sang FastAPI endpoint `/api/predict/`.
- Kiem tra FastAPI con song qua `/api/health/`.
- Luu ket qua du doan vao database Django:
  - `Patient`
  - `ClinicalRecord`
  - `ClinicalRecordLabel` neu du lieu co nhan that
  - `PredictionResult`
  - `RiskScoreDetail`

## Luong chinh

```text
mock_his random records
  -> FastAPI /api/predict/
  -> ket qua nguy co bien chung
  -> luu vao DB Django
  -> export vao data/training.csv
  -> dung cho retrain bang DVC/Airflow
```

## Auto-feed chay nen

Auto-feed khong con chay bang `setInterval` trong browser nua. Khi bam start hoac khi trang `/mock-his/` mo lan dau, UI goi endpoint dieu khien feed; vong lap gui ho so chay trong Django process o `mock_his/feed_runner.py`.

Trong moi truong local dev, feed cung duoc tu kich hoat khi chay Django bang:

```powershell
python manage.py runserver
```

Nghia la khong can mo trang `/mock-his/` truoc. Ban co the mo Dashboard/Patients truc tiep, mien la Django server va FastAPI server dang chay.

Cau hinh trong `settings.py`:

```python
MOCK_HIS_AUTO_START = True
MOCK_HIS_AUTO_START_INTERVAL = 5
MOCK_HIS_AUTO_START_DELAY = 3
MOCK_HIS_AUTO_START_UNLABELED = False
```

Auto-start chi chay voi lenh `runserver`, khong chay trong `test`, `migrate`, `makemigrations` hoac GitHub Actions.

Endpoint dieu khien:

```text
GET  /mock-his/feed/status/
POST /mock-his/feed/start/
POST /mock-his/feed/pause/
POST /mock-his/feed/resume/
POST /mock-his/feed/stop/
POST /mock-his/feed/reset/
```

Luu y: runner hien dung in-memory thread trong Django process, phu hop cho local demo/dev. Neu deploy production nhieu worker/process, can thay bang worker that nhu Celery/RQ/Huey hoac Airflow schedule.
