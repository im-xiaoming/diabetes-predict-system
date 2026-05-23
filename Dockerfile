FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN sed '/^pywin32==/d' requirements.txt > /tmp/requirements-docker.txt \
    && python -m pip install --upgrade pip \
    && python -m pip install -r /tmp/requirements-docker.txt

COPY . .
COPY docker/entrypoint.sh /entrypoint.sh

RUN sed -i 's/\r$//' /entrypoint.sh \
    && chmod +x /entrypoint.sh \
    && mkdir -p /app/runtime /app/staticfiles /app/mlruns

EXPOSE 8000 8001 5000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["django"]
