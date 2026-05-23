import json
from time import perf_counter

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from accounts.permissions import admin_required
from patients.models import ClinicalRecord, ClinicalRecordLabel, Patient
from predictions.models import PredictionResult, RequestLog, RiskScoreDetail
from .feed_runner import feed_runner
from .sample_loader import load_record, load_records, total_records
import requests

TARGETS = [
    ("NEP", "nep"),
    ("NEU", "neu"),
    ("RET", "ret"),
    ("CV", "cv"),
    ("PER VAS", "per_vas"),
]


def url(path):
    base = getattr(settings, "FASTAPI_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
    return f"{base}{path}"


def body(req):
    try:
        return json.loads(req.body.decode("utf-8") or "{}")
    except ValueError:
        return {}


def sex(v):
    s = str(v).strip().lower()
    if s in ["0", "female", "f", "nu", "nữ"]:
        return "female"
    return "male"


def score_level(score, label):
    if int(label) == 0:
        return "low"
    if float(score) >= 0.7:
        return "high"
    return "medium"


def get_val(data, *keys, default=None):
    for key in keys:
        if key in data:
            return data[key]
    return default


def to_float(v):
    if v is None or v == "":
        return 0.0
    return float(v)


def to_label(v):
    if v is None or v == "":
        return None
    return bool(int(float(v)))


def truth_data(rec):
    truth = rec.get("truth") or {}
    vals = {
        "nep": to_label(get_val(truth, "NEP", "nep")),
        "neu": to_label(get_val(truth, "NEU", "neu")),
        "ret": to_label(get_val(truth, "RET", "ret")),
        "cv": to_label(get_val(truth, "CV", "cv")),
        "per_vas": to_label(get_val(truth, "PER VAS", "per_vas")),
    }
    if any(v is None for v in vals.values()):
        return None
    return vals


def save_result(rec, res):
    data = rec["payload"]
    truth = truth_data(rec)
    labels = res.get("risk_labels", {})
    scores = res.get("risk_scores", {})
    level = str(res.get("risk_level") or "low").lower()
    if level not in ["low", "medium", "high"]:
        level = "low"

    with transaction.atomic():
        patient, _ = Patient.objects.update_or_create(
            id=int(float(rec["pid"])),
            defaults={
                "name": str(rec["name"]),
                "sex": sex(data["SEX"]),
                "level": level,
            },
        )
        cr = ClinicalRecord.objects.create(
            patient=patient,
            age=int(float(data["AGE"])),
            bmi=to_float(data["BMI"]),
            sp=to_float(data["SP"]),
            bp=to_float(data["BP"]),
            hba1c=to_float(data["HbA1c"]),
            fps=to_float(data["FPS"]),
            pps=to_float(data["PPS"]),
            fam_ho=str(data["FAMILY H/O"]),
            on_age=to_float(data["ONSET AGE"]),
            dia_life=str(data["DIA LIFE"]),
            smk=str(data["SMOKING"]),
            phy_act=str(data["PHY ACT"]),
            med_use=str(data["MED USE"]),
            med_adh=str(data["MED ADH"]),
            source="mock_his",
        )
        if truth:
            ClinicalRecordLabel.objects.create(
                clinical_record=cr,
                **truth,
                source="mendeley_mock",
            )
        pr = PredictionResult.objects.create(
            patient=patient,
            clinical_record=cr,
            model_name=str(res.get("model_name") or ""),
            model_version=str(res.get("model_version") or "v1"),
            risk_level=level,
            warning_message=str(res.get("warning_message") or ""),
        )
        rows = []
        latest = {}
        for target, field in TARGETS:
            sc = float(get_val(scores, target, field, default=0) or 0)
            lb = int(get_val(labels, target, field, default=0) or 0)
            latest[field] = bool(lb)
            rows.append(
                RiskScoreDetail(
                    prediction=pr,
                    target=target,
                    risk_score=sc,
                    risk_label=lb,
                    risk_level=score_level(sc, lb),
                )
            )
        RiskScoreDetail.objects.bulk_create(rows)
    return pr, bool(truth)


def call_predict(rec):
    endpoint = "/api/predict/"
    start = perf_counter()
    try:
        res = requests.post(url(endpoint), json=rec["payload"], timeout=30)
        latency = round((perf_counter() - start) * 1000, 2)
        try:
            data = res.json()
        except ValueError:
            data = {"detail": res.text}
    except requests.RequestException as exc:
        latency = round((perf_counter() - start) * 1000, 2)
        return {"ok": False, "saved": False, "idx": rec["idx"], "status_code": 503, "error": str(exc)}

    if res.status_code != 200:
        return {"ok": False, "saved": False, "idx": rec["idx"], "status_code": res.status_code, "error": data}

    pred, truth_saved = save_result(rec, data)
    RequestLog.objects.create(
        prediction=pred,
        endpoint=endpoint,
        status_code=res.status_code,
        latency_ms=latency,
    )
    return {
        "ok": True,
        "saved": True,
        "truth_saved": truth_saved,
        "idx": rec["idx"],
        "status_code": res.status_code,
        "patient_id": int(float(rec["pid"])),
        "prediction_id": pred.id,
        "response": data,
    }


def without_truth(rec):
    out = dict(rec)
    out.pop("truth", None)
    return out


def page_context(request, *, unlabeled=False):
    feed_state = feed_runner.status()
    start_offset = int(feed_state.get("next_idx", 0) or 0)
    records = load_records(offset=start_offset, limit=20)
    if unlabeled:
        records = [without_truth(rec) for rec in records]
    return {
        "records": records,
        "total": total_records(),
        "start_offset": start_offset,
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
        "feed_start_url": reverse("mock-his-feed-start"),
        "feed_pause_url": reverse("mock-his-feed-pause"),
        "feed_resume_url": reverse("mock-his-feed-resume"),
        "feed_stop_url": reverse("mock-his-feed-stop"),
        "feed_reset_url": reverse("mock-his-feed-reset"),
        "feed_status_url": reverse("mock-his-feed-status"),
        "mode_label": "No ground truth labels" if unlabeled else "Ground truth labels included",
        "unlabeled": unlabeled,
    }


@admin_required
def mock_his_view(request):
    return render(request, "mock_his/mock_his.html", page_context(request))


@admin_required
def his_inference_view(request):
    return render(request, "mock_his/mock_his.html", page_context(request, unlabeled=True))


@admin_required
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


@admin_required
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


@admin_required
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


@admin_required
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


@admin_required
@require_GET
def records_view(request):
    offset = int(request.GET.get("offset", 0))
    limit = int(request.GET.get("limit", 20))
    limit = max(1, min(limit, 100))
    records = load_records(offset=offset, limit=limit)
    return JsonResponse(
        {
            "ok": True,
            "offset": offset,
            "limit": limit,
            "total": total_records(),
            "records": records,
        }
    )


@admin_required
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


@admin_required
@require_GET
def health_view(request):
    try:
        res = requests.get(url("/api/health/"), timeout=10)
        data = res.json()
        return JsonResponse({"ok": res.status_code == 200, "status_code": res.status_code, "response": data})
    except requests.RequestException as exc:
        return JsonResponse({"ok": False, "status_code": 503, "error": str(exc)}, status=503)


@admin_required
@require_GET
def feed_status_view(request):
    return JsonResponse({"ok": True, "feed": feed_runner.status()})


@admin_required
@require_POST
def feed_start_view(request):
    data = body(request)
    interval = int(data.get("interval", 5))
    reset = bool(data.get("reset", False))
    unlabeled = bool(data.get("unlabeled", False))
    state = feed_runner.start(interval=interval, reset=reset, unlabeled=unlabeled)
    return JsonResponse({"ok": True, "feed": state})


@admin_required
@require_POST
def feed_pause_view(request):
    return JsonResponse({"ok": True, "feed": feed_runner.pause()})


@admin_required
@require_POST
def feed_resume_view(request):
    return JsonResponse({"ok": True, "feed": feed_runner.resume()})


@admin_required
@require_POST
def feed_stop_view(request):
    return JsonResponse({"ok": True, "feed": feed_runner.stop()})


@admin_required
@require_POST
def feed_reset_view(request):
    return JsonResponse({"ok": True, "feed": feed_runner.reset()})
