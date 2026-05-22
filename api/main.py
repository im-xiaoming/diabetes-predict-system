import traceback
import os
from pathlib import Path
from time import perf_counter

import django
from fastapi import FastAPI, HTTPException

from api.schemas import IngestRequest, IngestResponse, PredictRequest, PredictResponse
from ml.predictor import predict_one


ROOT_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT_DIR / "ml" / "artifacts" / "model.pkl"

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "diabetes_predict_system.settings")
django.setup()

from predictions.services import save_prediction

app = FastAPI(title="Diabetes Complication Prediction API")


def to_dict(req):
    if hasattr(req, "model_dump"):
        return req.model_dump(by_alias=True)
    return req.dict(by_alias=True)


@app.get("/api/health/")
def health():
    exists = MODEL_PATH.exists()
    return {
        "status": "ok",
        "model_file_exists": exists,
        "model_path": str(MODEL_PATH),
    }


@app.post("/api/predict/", response_model=PredictResponse)
def predict(req: PredictRequest):
    if not MODEL_PATH.exists():
        raise HTTPException(status_code=503, detail="Model file not found. Run python ml/train.py first.")
    try:
        return predict_one(to_dict(req))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="Model file not found. Run python ml/train.py first.") from exc
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=503, detail=f"Prediction service unavailable: {exc}") from exc


@app.post("/api/ingest/", response_model=IngestResponse)
def ingest(req: IngestRequest):
    if not MODEL_PATH.exists():
        raise HTTPException(status_code=503, detail="Model file not found. Run python ml/train.py first.")
    data = to_dict(req)
    patient_id = data.pop("patient_id")
    patient_name = data.pop("patient_name")
    source = data.pop("source", "his")
    source_idx = data.pop("source_idx", None)
    truth = data.pop("truth", None)
    start = perf_counter()
    try:
        res = predict_one(data)
        latency = round((perf_counter() - start) * 1000, 2)
        return save_prediction(
            patient_id=patient_id,
            patient_name=patient_name,
            ft=data,
            res=res,
            source=source,
            source_idx=source_idx,
            truth=truth,
            endpoint="/api/ingest/",
            status_code=200,
            latency_ms=latency,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="Model file not found. Run python ml/train.py first.") from exc
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=503, detail=f"Ingest service unavailable: {exc}") from exc
