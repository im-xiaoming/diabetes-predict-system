![Demo](images/image.png)

# Đan Đường Dự Tri Huyết Đường

Đây là pháp trận dự đoán nguy cơ biến chứng tiểu đường, lấy Django làm chính điện, FastAPI làm truyền lệnh sứ, MLflow ghi công pháp tu luyện, DVC giữ linh thạch dữ liệu, Mock HIS mô phỏng y viện, Airflow điều khiển lịch tái luyện, Prometheus và Grafana quan sát khí mạch hệ thống.

## Khai Môn Tại Bản Địa

```powershell
cd C:\diabetes\diabetes_predict_system
python manage.py migrate
python manage.py runserver
```

Chính điện: http://127.0.0.1:8000

## Khởi Động Docker Pháp Trận

```powershell
cd C:\diabetes\diabetes_predict_system
docker compose up --build
```

Các linh đài:

- Django: http://127.0.0.1:8000
- FastAPI: http://127.0.0.1:8001/docs
- MLflow: http://127.0.0.1:5000
- Prometheus: http://127.0.0.1:9090
- Grafana: http://127.0.0.1:3000

## Thiên Cơ Airflow

```powershell
cd C:\diabetes\diabetes_predict_system\airflow
docker compose --env-file ../.env up --build
```

Airflow đạo trường: http://127.0.0.1:8080

## Luyện Đan Mô Hình

```powershell
python -u ml/train.py --data data/training.csv --config configs/model_training_config.json
```

Đan phương nằm tại `configs/model_training_config.json`. Công đoạn tiền xử lý có thể vận hành bằng pandas hoặc PySpark qua pháp ấn `preprocessing_backend`.

## Bí Tịch Phụ Lục

- Docker pháp quyết: `DOCKER.md`
- DVC linh phổ: `DVC.md`
- ML công pháp: `ml/README.md`
