FROM apache/airflow:3.2.1-python3.11

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends git openjdk-21-jre-headless \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 \
    PYSPARK_PYTHON=python \
    PYSPARK_DRIVER_PYTHON=python

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
    pyarrow==23.0.1 \
    pyspark==4.0.1 \
    PyYAML==6.0.3 \
    scikit-learn==1.8.0
