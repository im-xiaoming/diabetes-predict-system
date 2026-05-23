python -m uvicorn api.main:app --port 8001

python manage.py makemigrations
python manage.py migrate
python manage.py runserver
dvc pull -r origin

mlflow ui --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns
docker compose -f monitoring/docker-compose.yml up -d

cd airflow
Copy-Item .env.example .env
docker compose build
docker compose up airflow-init
docker compose up

