app `mock_his` dùng để **giả lập HIS** (*Hospital Information System* - hệ thống thông tin bệnh viện).

Nó không phải app nghiệp vụ chính, mà là app **demo/test luồng dữ liệu bệnh viện gửi hồ sơ bệnh nhân sang hệ thống dự đoán tiểu đường**.

Cụ thể:

- Đọc dữ liệu bệnh nhân mẫu từ `data/data.csv` qua [sample_loader.py](C:/diabetes/diabetes_predict_system/mock_his/sample_loader.py).
- Hiển thị giao diện mô phỏng tại `/mock-his/` qua [views.py](C:/diabetes/diabetes_predict_system/mock_his/views.py:163).
- Gửi từng hồ sơ hoặc gửi hàng loạt sang FastAPI endpoint `/api/predict/`.
- Kiểm tra FastAPI còn sống qua `/api/health/`.
- Sau khi nhận kết quả dự đoán, lưu vào database Django:
  - `Patient`
  - `ClinicalRecord`
  - `PredictionResult`
  - `RiskScoreDetail`
  - `PatientRiskStatus`

Luồng chính là:

```text
data.csv
  -> mock_his
  -> FastAPI /api/predict/
  -> kết quả nguy cơ biến chứng
  -> lưu vào DB Django
  -> hiển thị ở Patients/Dashboard
```

Trong UI, trang Mock HIS còn có auto-feed: khi mở trang, nó tự gửi dần hồ sơ bệnh nhân sang FastAPI theo interval. Phần này nằm trong template [mock_his.html](C:/diabetes/diabetes_predict_system/mock_his/templates/mock_his/mock_his.html).

Nói ngắn gọn: `mock_his` được dùng để **giả lập nguồn dữ liệu bệnh viện**, giúp test/demo hệ thống dự đoán mà chưa cần tích hợp với HIS thật.
