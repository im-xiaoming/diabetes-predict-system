mlflow ui --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns
python .\ml\train.py --tune --n-trials 5 --timeout 600 --register