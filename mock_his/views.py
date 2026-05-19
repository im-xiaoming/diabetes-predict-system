import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from patients.models import ClinicalRecord, Patient, PatientRiskStatus
from predictions.models import PredictionResult, RiskScoreDetail
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


def save_result(rec, res):
    data = rec["payload"]
    labels = res.get("risk_labels", {})
    scores = res.get("risk_scores", {})
    level = str(res.get("risk_level") or "low").lower()
    if level not in ["low", "medium", "high", "very_high"]:
        level = "low"

    with transaction.atomic():
        patient, _ = Patient.objects.update_or_create(
            id=int(float(rec["pid"])),
            defaults={
                "name": str(rec["name"]),
                "age": int(float(data["AGE"])),
                "sex": sex(data["SEX"]),
                "level": level,
            },
        )
        cr = ClinicalRecord.objects.create(
            patient=patient,
            age=int(float(data["AGE"])),
            sex=str(data["SEX"]),
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
        PatientRiskStatus.objects.update_or_create(
            patient=patient,
            defaults={**latest, "source": "prediction"},
        )
    return pr.id


def call_predict(rec):
    try:
        res = requests.post(url("/api/predict/"), json=rec["payload"], timeout=30)
        try:
            data = res.json()
        except ValueError:
            data = {"detail": res.text}
    except requests.RequestException as exc:
        return {"ok": False, "saved": False, "idx": rec["idx"], "status_code": 503, "error": str(exc)}

    if res.status_code != 200:
        return {"ok": False, "saved": False, "idx": rec["idx"], "status_code": res.status_code, "error": data}

    pred_id = save_result(rec, data)
    return {
        "ok": True,
        "saved": True,
        "idx": rec["idx"],
        "status_code": res.status_code,
        "patient_id": int(float(rec["pid"])),
        "prediction_id": pred_id,
        "response": data,
    }


@login_required(login_url="login")
def mock_his_view(request):
    records = load_records(offset=0, limit=20)
    return render(request, "mock_his/mock_his.html", {"records": records, "total": total_records()})


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


@login_required(login_url="login")
@require_GET
def health_view(request):
    try:
        res = requests.get(url("/api/health/"), timeout=10)
        data = res.json()
        return JsonResponse({"ok": res.status_code == 200, "status_code": res.status_code, "response": data})
    except requests.RequestException as exc:
        return JsonResponse({"ok": False, "status_code": 503, "error": str(exc)}, status=503)
