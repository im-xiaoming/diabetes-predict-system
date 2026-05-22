import traceback
from pathlib import Path

from fastapi import FastAPI, HTTPException

from api.metrics import metrics_response, track_http
from api.schemas import PredictRequest, PredictResponse
from ml.predictor import predict_one


ROOT_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT_DIR / "ml" / "artifacts" / "model.pkl"

app = FastAPI(title="Diabetes Complication Prediction API")


@app.middleware("http")
async def metrics_middleware(req, call_next):
    return await track_http(req, call_next)


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


@app.get("/metrics", include_in_schema=False)
def metrics():
    return metrics_response()


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
