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
- MLflow: http://127.0.0.1:5001
- Prometheus: http://127.0.0.1:9090
- Grafana: http://127.0.0.1:3000

## Thiên Cơ Airflow

```powershell
cd C:\diabetes\diabetes_predict_system\airflow
docker compose --env-file ../.env up --build
```

Airflow đạo trường: http://127.0.0.1:8080

## Luyện Đan Mô Hình

Đan phương nằm tại `configs/model_training_config.json`. Công đoạn tiền xử lý có thể vận hành bằng pandas hoặc PySpark qua pháp ấn `preprocessing_backend`.

## Bí Tịch Phụ Lục

- Docker pháp quyết: `DOCKER.md`
- DVC linh phổ: `DVC.md`
- ML công pháp: `ml/README.md`

## Hạ Sơn Bằng Docker Hub

Nếu không muốn build lại từ source, hãy dùng bộ file đã chuẩn bị trong thư mục `docker-hub/`. Bộ này kéo image đã push lên Docker Hub và khởi động các dịch vụ chính bằng Docker Compose.

```powershell
cd C:\diabetes\diabetes_predict_system\docker-hub
copy .env.example .env
docker compose pull
docker compose up -d
```

Image mặc định:

```text
nguyenminh079/diabetes-predict-system:latest
```

Địa chỉ sau khi khởi động:

- Django: http://127.0.0.1:8000
- FastAPI docs: http://127.0.0.1:8001/docs
- MLflow: http://127.0.0.1:5001
- Prometheus: http://127.0.0.1:9090
- Grafana: http://127.0.0.1:3000

Tài khoản mặc định:

- Django admin: `admin / 1`
- Grafana: `admin / admin`

Xem hướng dẫn đầy đủ tại `docker-hub/DOCKER-HUB.md`.
