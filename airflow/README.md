# Airflow

Airflow is kept inside the project repository so DAGs and orchestration config can be versioned with the Django code. It is not a Django app and should not be added to `INSTALLED_APPS`.

Use this folder for:

- `dags/`: Airflow DAG definitions.
- `plugins/`: custom Airflow plugins.
- `docker-compose.yaml`: local Airflow stack.

Runtime files are intentionally ignored:

- `logs/`
- `config/airflow.cfg`
- `.env`

To run locally:

```powershell
cd airflow
Copy-Item .env.example .env
docker compose up airflow-init
docker compose up
```

Airflow UI: http://localhost:8080

Default local credentials are `airflow` / `airflow` unless overridden in `.env`.
