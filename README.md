# Diabetes Predict System

Diabetes Predict System là hệ thống hỗ trợ dự đoán nguy cơ biến chứng tiểu đường, kết hợp ứng dụng quản lý bệnh án, dịch vụ suy luận mô hình và quy trình MLOps để theo dõi, huấn luyện lại và triển khai mô hình.

Dự án sử dụng Django cho giao diện và quản lý dữ liệu bệnh án, FastAPI cho API suy luận, scikit-learn cho mô hình dự đoán, Optuna để tối ưu tham số, PySpark hoặc pandas cho tiền xử lý dữ liệu, MLflow để ghi nhận thí nghiệm, DVC để quản lý dữ liệu và model artifact.

Bên cạnh đó, hệ thống có Mock HIS để mô phỏng luồng dữ liệu bệnh viện, HIS Inference để tiếp nhận hồ sơ cần dự đoán, SQLite hoặc PostgreSQL để lưu lịch sử suy luận, Airflow để tự động hóa quy trình tái huấn luyện, Prometheus và Grafana để giám sát vận hành. Docker và Docker Hub được dùng để đóng gói, phân phối và khởi chạy các dịch vụ một cách nhất quán.

Mục tiêu của hệ thống là hỗ trợ nhân viên y tế nhận diện sớm hồ sơ có nguy cơ cao, ưu tiên theo dõi các trường hợp cần chú ý và cung cấp thêm dữ liệu tham khảo cho quá trình ra quyết định. Kết quả dự đoán chỉ mang tính hỗ trợ, không thay thế chẩn đoán chuyên môn của bác sĩ.

## Chạy Trên Máy Cục Bộ

```powershell
cd C:\diabetes\diabetes_predict_system
python manage.py migrate
python manage.py runserver
```

Ứng dụng Django: http://127.0.0.1:8000

## Chạy Bằng Docker Compose

```powershell
cd C:\diabetes\diabetes_predict_system
docker compose up --build
```

Các dịch vụ sau khi khởi động:

- Django: http://127.0.0.1:8000
- FastAPI: http://127.0.0.1:8001/docs
- MLflow: http://127.0.0.1:5001
- Prometheus: http://127.0.0.1:9090
- Grafana: http://127.0.0.1:3000

## Khởi Động Airflow

```powershell
cd C:\diabetes\diabetes_predict_system\airflow
docker compose --env-file ../.env up --build
```

Airflow: http://127.0.0.1:8080

## Huấn Luyện Mô Hình

Cấu hình huấn luyện nằm tại `configs/model_training_config.json`. Bước tiền xử lý có thể chạy bằng pandas hoặc PySpark thông qua tùy chọn `preprocessing_backend`.

## Tài Liệu Liên Quan

- Docker: `DOCKER.md`
- DVC: `DVC.md`
- Machine Learning: `ml/README.md`

## Chạy Bằng Image Từ Docker Hub

Nếu không muốn build lại từ source, có thể dùng bộ file đã chuẩn bị trong thư mục `docker-hub/`. Bộ cấu hình này kéo image đã được push lên Docker Hub và khởi động các dịch vụ chính bằng Docker Compose.

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
