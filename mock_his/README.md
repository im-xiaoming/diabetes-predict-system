# Mock HIS

App `mock_his` dùng để giả lập HIS (*Hospital Information System* - hệ thống thông tin bệnh viện).

Đây không phải app nghiệp vụ chính, mà là app demo/test luồng dữ liệu bệnh viện gửi hồ sơ bệnh nhân sang hệ thống dự đoán biến chứng tiểu đường.

## Chức năng

- Đọc dữ liệu bệnh nhân mẫu từ `data/data.csv` qua `mock_his/sample_loader.py`.
- Hiển thị giao diện mô phỏng tại `/mock-his/`.
- Gửi từng hồ sơ hoặc gửi hàng loạt sang FastAPI endpoint `/api/predict/`.
- Kiểm tra FastAPI còn sống qua `/api/health/`.
- Lưu kết quả dự đoán vào database Django:
  - `Patient`
  - `ClinicalRecord`
  - `ClinicalRecordLabel` nếu dữ liệu có nhãn thật
  - `PredictionResult`
  - `RiskScoreDetail`

## Luồng chính

```text
data.csv
  -> mock_his
  -> FastAPI /api/predict/
  -> kết quả nguy cơ biến chứng
  -> lưu vào DB Django
  -> hiển thị ở Patients/Dashboard
```

## Auto-feed chạy nền

Auto-feed không còn chạy bằng `setInterval` trong browser nữa. Khi bấm start hoặc khi trang `/mock-his/` mở lần đầu, UI gọi endpoint điều khiển feed; vòng lặp gửi hồ sơ chạy trong Django process ở `mock_his/feed_runner.py`.

Trong môi trường local dev, feed cũng được tự kích hoạt khi chạy Django bằng:

```powershell
python manage.py runserver
```

Nghĩa là không cần mở trang `/mock-his/` trước. Bạn có thể mở Dashboard/Patients trực tiếp, miễn là Django server và FastAPI server đang chạy.

Vì vậy nếu chuyển sang trang khác, đóng tab Mock HIS, hoặc mở Dashboard/Patients, feed vẫn tiếp tục chạy miễn là:

- Django server vẫn đang chạy.
- FastAPI server vẫn đang chạy.
- Django process không bị restart.

Cấu hình trong `settings.py`:

```python
MOCK_HIS_AUTO_START = True
MOCK_HIS_AUTO_START_INTERVAL = 5
MOCK_HIS_AUTO_START_DELAY = 3
MOCK_HIS_AUTO_START_UNLABELED = False
```

Auto-start chỉ chạy với lệnh `runserver`, không chạy trong `test`, `migrate`, `makemigrations` hoặc GitHub Actions.

Các endpoint điều khiển:

```text
GET  /mock-his/feed/status/
POST /mock-his/feed/start/
POST /mock-his/feed/pause/
POST /mock-his/feed/resume/
POST /mock-his/feed/stop/
POST /mock-his/feed/reset/
```

Lưu ý: runner hiện dùng in-memory thread trong Django process, phù hợp cho local demo/dev. Nếu deploy production nhiều worker/process, cần thay bằng worker thật như Celery/RQ/Huey hoặc Airflow schedule.
