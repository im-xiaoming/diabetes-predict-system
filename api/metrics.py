from time import perf_counter

from fastapi import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest


ROUTES = {
    "/api/health/": "/api/health/",
    "/api/predict/": "/api/predict/",
    "/metrics": "/metrics",
}

HTTP_REQ = Counter(
    "diabetes_http_requests_total",
    "FastAPI HTTP requests.",
    ["method", "route", "status"],
)
HTTP_SEC = Histogram(
    "diabetes_http_request_duration_seconds",
    "FastAPI HTTP request latency.",
    ["method", "route"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)
PRED_REQ = Counter(
    "diabetes_prediction_requests_total",
    "Prediction endpoint outcomes.",
    ["outcome"],
)


def route_label(req):
    return ROUTES.get(req.url.path, "other")


async def track_http(req, call_next):
    start = perf_counter()
    route = route_label(req)
    status = 500
    try:
        res = await call_next(req)
        status = res.status_code
        return res
    finally:
        elapsed = perf_counter() - start
        HTTP_REQ.labels(req.method, route, str(status)).inc()
        HTTP_SEC.labels(req.method, route).observe(elapsed)
        if route == "/api/predict/":
            outcome = "success" if status < 400 else "error"
            PRED_REQ.labels(outcome).inc()


def metrics_response():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
