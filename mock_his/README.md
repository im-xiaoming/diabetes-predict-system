`mock_his` giả lập nguồn hồ sơ từ HIS để kiểm tra luồng ingest trước khi tích hợp với hệ thống bệnh viện thật.

Luồng chính:

```text
data.csv
  -> Mock HIS
  -> FastAPI /api/ingest/
  -> predict
  -> Django database
  -> Alert Engine
  -> Dashboard / Patients / Alerts
```

Mock HIS gửi metadata bệnh nhân, 15 feature lâm sàng và nhãn thật chỉ có trong dữ liệu mock để phục vụ retrain sau này. Nhãn thật không tham gia dự đoán và không dùng để tạo alert.

Sau mỗi ingest thành công, database lưu:

- `Patient`
- `ClinicalRecord`
- `ClinicalRecordLabel` nếu record mock có ground truth
- `PredictionResult`
- `RiskScoreDetail`
- `RequestLog`
- `Alert` cho biến chứng nguy cơ cao
- `WatchlistItem` cho biến chứng nguy cơ trung bình

Trang `/mock-his/` dùng để quan sát hồ sơ mẫu và test feed. Feed nền có thể chạy bằng:

```powershell
python manage.py run_mock_his_feed --interval 5
```
