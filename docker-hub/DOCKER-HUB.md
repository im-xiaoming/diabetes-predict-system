# Chạy image từ Docker Hub

Thư mục này dùng để kéo image đã push lên Docker Hub và chạy app mà không cần build lại từ source code.

## Chạy nhanh

```powershell
cd C:\diabetes\diabetes_predict_system\docker-hub
copy .env.example .env
docker compose pull
docker compose up -d
```

Lần đầu khởi động sẽ tạo hoặc cập nhật tài khoản admin:

```text
admin / 1
```

## Địa chỉ dịch vụ

- Django: http://127.0.0.1:8000
- FastAPI docs: http://127.0.0.1:8001/docs
- MLflow: http://127.0.0.1:5000
- Prometheus: http://127.0.0.1:9090
- Grafana: http://127.0.0.1:3000

Tài khoản Grafana mặc định:

```text
admin / admin
```

## Image

Mặc định `docker-compose.yml` dùng image:

```text
nguyenminh079/diabetes-predict-system:latest
```

Nếu muốn dùng tag khác, sửa biến `APP_IMAGE` trong file `.env`.

## Quản lý container

```powershell
docker compose ps
docker compose logs -f django
docker compose logs -f api
docker compose down
```

Xóa toàn bộ dữ liệu runtime local:

```powershell
docker compose down -v
```

## DVC và model artifact

Image có sẵn code và artifact tại thời điểm build. Nếu muốn container tự pull artifact mới từ DVC remote khi khởi động, sửa `.env`:

```text
DVC_PULL=True
DVC_REMOTE=origin
AWS_ACCESS_KEY_ID=<dagshub-access-key>
AWS_SECRET_ACCESS_KEY=<dagshub-secret-key>
```

Không commit file `.env` có chứa credential.

## Ghi chú về Airflow

Bộ file này chỉ chạy app chính. Airflow stack chưa được đóng gói ở đây, vì Airflow image hiện tại cần cấu trúc DAG/project riêng. Nếu cần chạy Airflow bằng Docker Hub, hãy build và push riêng image Airflow có chứa project code, sau đó tạo compose riêng cho Airflow.
