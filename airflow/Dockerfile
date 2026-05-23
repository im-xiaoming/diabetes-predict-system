FROM apache/airflow:3.2.1-python3.11

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

RUN pip install --no-cache-dir \
    Django==5.2.14 \
    djangorestframework==3.17.1 \
    dvc==3.67.1 \
    dvc-s3==3.3.0 \
    joblib==1.5.3 \
    mlflow==3.12.0 \
    numpy==1.26.4 \
    optuna==4.8.0 \
    pandas==2.3.3 \
    psycopg2-binary==2.9.11 \
    PyYAML==6.0.3 \
    scikit-learn==1.8.0
