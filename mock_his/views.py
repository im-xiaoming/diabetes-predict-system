import json

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from patients.models import ClinicalRecord

from .sample_loader import load_record, load_records, total_records


def url(path):
    base = getattr(settings, "FASTAPI_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
    return f"{base}{path}"


def body(req):
    try:
        return json.loads(req.body.decode("utf-8") or "{}")
    except ValueError:
        return {}


def saved_result(rec):
    idx = rec.get("idx")
    if idx is None:
        return None
    cr = ClinicalRecord.objects.filter(source="mock_his", source_idx=idx).order_by("-created_at").first()
    if not cr:
        return None
    pred = cr.predictions.order_by("-created_at").first()
    if not pred:
        return None
    scores = {row.target: row.risk_score for row in pred.scores.all()}
    labels = {row.target: row.risk_label for row in pred.scores.all()}
    return {
        "ok": True,
        "saved": True,
        "already_saved": True,
        "truth_saved": hasattr(cr, "label"),
        "idx": idx,
        "status_code": 200,
        "patient_id": cr.patient_id,
        "prediction_id": pred.id,
        "alert_ids": list(pred.alerts.values_list("id", flat=True)),
        "watchlist_ids": list(pred.watchlist_items.values_list("id", flat=True)),
        "response": {
            "risk_scores": scores,
            "risk_labels": labels,
            "risk_level": pred.risk_level,
            "warning_message": pred.warning_message,
            "model_name": pred.model_name,
            "model_version": pred.model_version,
            "saved": True,
            "already_saved": True,
            "patient_id": cr.patient_id,
            "clinical_record_id": cr.id,
            "prediction_id": pred.id,
        },
    }


def ingest_payload(rec):
    return {
        **rec["payload"],
        "patient_id": int(float(rec["pid"])),
        "patient_name": str(rec["name"]),
        "source": "mock_his",
        "source_idx": int(rec["idx"]),
        "truth": rec.get("truth") or None,
    }


def call_predict(rec):
    old = saved_result(rec)
    if old:
        return old

    endpoint = "/api/ingest/"
    try:
        res = requests.post(url(endpoint), json=ingest_payload(rec), timeout=30)
        try:
            data = res.json()
        except ValueError:
            data = {"detail": res.text}
    except requests.RequestException as exc:
        return {"ok": False, "saved": False, "idx": rec["idx"], "status_code": 503, "error": str(exc)}

    if res.status_code != 200:
        return {"ok": False, "saved": False, "idx": rec["idx"], "status_code": res.status_code, "error": data}

    return {
        "ok": True,
        "saved": data.get("saved", False),
        "already_saved": data.get("already_saved", False),
        "truth_saved": data.get("truth_saved", False),
        "idx": rec["idx"],
        "status_code": res.status_code,
        "patient_id": data.get("patient_id"),
        "prediction_id": data.get("prediction_id"),
        "alert_ids": data.get("alert_ids", []),
        "watchlist_ids": data.get("watchlist_ids", []),
        "response": data,
    }


def without_truth(rec):
    out = dict(rec)
    out.pop("truth", None)
    return out


def page_context(request, *, unlabeled=False):
    records = load_records(offset=0, limit=20)
    if unlabeled:
        records = [without_truth(rec) for rec in records]
    return {
        "records": records,
        "total": total_records(),
        "page_title": "Unlabeled HIS Feed" if unlabeled else "Mock HIS Simulation",
        "page_subtitle": (
            "Gửi hồ sơ không nhãn đến FastAPI để model tạo dự đoán và lưu PredictionResult."
            if unlabeled
            else "Auto fake real-time feed: Mock HIS starts sending patient records to FastAPI when this page opens."
        ),
        "records_title": "Unlabeled Patient Records" if unlabeled else "Patient Records Ready for Transmission",
        "send_url": reverse("his-inference-send" if unlabeled else "mock-his-send"),
        "bulk_url": reverse("his-inference-send-bulk" if unlabeled else "mock-his-send-bulk"),
        "health_url": reverse("mock-his-health"),
        "records_url": reverse("his-inference-records" if unlabeled else "mock-his-records"),
        "mode_label": "No ground truth labels" if unlabeled else "Ground truth labels included",
        "unlabeled": unlabeled,
    }


@login_required(login_url="login")
def mock_his_view(request):
    return render(request, "mock_his/mock_his.html", page_context(request))


@login_required(login_url="login")
def his_inference_view(request):
    return render(request, "mock_his/mock_his.html", page_context(request, unlabeled=True))


@login_required(login_url="login")
@require_POST
def send_one_view(request):
    data = body(request)
    idx = int(data.get("idx", 0))
    if idx < 0:
        return JsonResponse({"ok": False, "saved": False, "error": "Invalid record index"}, status=400)
    rec = load_record(idx)
    if not rec:
        return JsonResponse({"ok": False, "saved": False, "idx": idx, "error": "Record not found"}, status=404)
    if not rec["ready"]:
        return JsonResponse({"ok": False, "saved": False, "idx": idx, "skipped": True, "error": "Record has missing values"}, status=400)
    out = call_predict(rec)
    return JsonResponse(out, status=200 if out["ok"] else 502)


@login_required(login_url="login")
@require_POST
def send_unlabeled_one_view(request):
    data = body(request)
    idx = int(data.get("idx", 0))
    if idx < 0:
        return JsonResponse({"ok": False, "saved": False, "error": "Invalid record index"}, status=400)
    rec = load_record(idx)
    if not rec:
        return JsonResponse({"ok": False, "saved": False, "idx": idx, "error": "Record not found"}, status=404)
    if not rec["ready"]:
        return JsonResponse({"ok": False, "saved": False, "idx": idx, "skipped": True, "error": "Record has missing values"}, status=400)
    out = call_predict(without_truth(rec))
    return JsonResponse(out, status=200 if out["ok"] else 502)


@login_required(login_url="login")
@require_POST
def send_bulk_view(request):
    data = body(request)
    count = int(data.get("count", 20))
    offset = int(data.get("offset", 0))
    records = [rec for rec in load_records(offset=offset, limit=count) if rec["ready"]]
    rows = [call_predict(rec) for rec in records]
    ok = sum(1 for row in rows if row["ok"])
    out = {
        "ok": ok == len(rows),
        "total": len(rows),
        "success": ok,
        "failed": len(rows) - ok,
        "results": rows,
    }
    return JsonResponse(out, status=200 if out["ok"] else 502)


@login_required(login_url="login")
@require_POST
def send_unlabeled_bulk_view(request):
    data = body(request)
    count = int(data.get("count", 20))
    offset = int(data.get("offset", 0))
    records = [without_truth(rec) for rec in load_records(offset=offset, limit=count) if rec["ready"]]
    rows = [call_predict(rec) for rec in records]
    ok = sum(1 for row in rows if row["ok"])
    out = {
        "ok": ok == len(rows),
        "total": len(rows),
        "success": ok,
        "failed": len(rows) - ok,
        "results": rows,
    }
    return JsonResponse(out, status=200 if out["ok"] else 502)


@login_required(login_url="login")
@require_GET
def records_view(request):
    offset = int(request.GET.get("offset", 0))
    limit = int(request.GET.get("limit", 20))
    limit = max(1, min(limit, 100))
    records = mark_records(load_records(offset=offset, limit=limit))
    return JsonResponse(
        {
            "ok": True,
            "offset": offset,
            "limit": limit,
            "total": total_records(),
            "records": records,
        }
    )


@login_required(login_url="login")
@require_GET
def unlabeled_records_view(request):
    offset = int(request.GET.get("offset", 0))
    limit = int(request.GET.get("limit", 20))
    limit = max(1, min(limit, 100))
    records = [without_truth(rec) for rec in load_records(offset=offset, limit=limit)]
    return JsonResponse(
        {
            "ok": True,
            "offset": offset,
            "limit": limit,
            "total": total_records(),
            "records": records,
        }
    )


@login_required(login_url="login")
@require_GET
def health_view(request):
    try:
        res = requests.get(url("/api/health/"), timeout=10)
        data = res.json()
        return JsonResponse({"ok": res.status_code == 200, "status_code": res.status_code, "response": data})
    except requests.RequestException as exc:
        return JsonResponse({"ok": False, "status_code": 503, "error": str(exc)}, status=503)
