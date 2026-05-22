from django.db import transaction

from alerts.services import create_workflow_items
from patients.models import ClinicalRecord, ClinicalRecordLabel, Patient

from .models import PredictionResult, RequestLog, RiskScoreDetail


TARGETS = [
    ("NEP", "nep"),
    ("NEU", "neu"),
    ("RET", "ret"),
    ("CV", "cv"),
    ("PER VAS", "per_vas"),
]


def get_val(data, *keys, default=None):
    for key in keys:
        if key in data:
            return data[key]
    return default


def sex_val(v):
    val = str(v).strip().lower()
    if val in ["0", "female", "f", "nu", "nữ"]:
        return "female"
    return "male"


def to_float(v):
    if v is None or v == "":
        return 0.0
    return float(v)


def to_label(v):
    if v is None or v == "":
        return None
    return bool(int(float(v)))


def level_val(v):
    val = str(v or "low").lower()
    if val in ["low", "medium", "high", "very_high"]:
        return val
    return "low"


def score_level(score, label):
    if int(label) == 0:
        return "low"
    if float(score) >= 0.7:
        return "high"
    return "medium"


def truth_vals(truth):
    if not truth:
        return None
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


def find_saved(patient_id, source, source_idx):
    if source_idx is None:
        return None
    cr = (
        ClinicalRecord.objects.filter(patient_id=patient_id, source=source, source_idx=source_idx)
        .order_by("-created_at")
        .first()
    )
    if not cr:
        return None
    return cr.predictions.order_by("-created_at").first()


def result_data(pred, already_saved=False, req=None):
    scores = {row.target: row.risk_score for row in pred.scores.all()}
    labels = {row.target: row.risk_label for row in pred.scores.all()}
    alerts = list(pred.alerts.values_list("id", flat=True))
    watch = list(pred.watchlist_items.values_list("id", flat=True))
    out = {
        "risk_scores": scores,
        "risk_labels": labels,
        "risk_level": pred.risk_level,
        "warning_message": pred.warning_message,
        "model_name": pred.model_name,
        "model_version": pred.model_version,
        "saved": True,
        "already_saved": already_saved,
        "patient_id": pred.patient_id,
        "clinical_record_id": pred.clinical_record_id,
        "prediction_id": pred.id,
        "alert_ids": alerts,
        "watchlist_ids": watch,
        "truth_saved": ClinicalRecordLabel.objects.filter(clinical_record=pred.clinical_record).exists(),
    }
    if req:
        out["request_log_id"] = req.id
    return out


def save_prediction(patient_id, patient_name, ft, res, source="his", source_idx=None, truth=None, endpoint="", status_code=200, latency_ms=0):
    old = find_saved(patient_id, source, source_idx)
    if old:
        req = None
        if endpoint:
            req = RequestLog.objects.create(
                prediction=old,
                endpoint=endpoint,
                status_code=status_code,
                latency_ms=latency_ms,
            )
        return result_data(old, already_saved=True, req=req)

    labels = res.get("risk_labels", {})
    scores = res.get("risk_scores", {})
    level = level_val(res.get("risk_level"))
    truth = truth_vals(truth)

    with transaction.atomic():
        patient, _ = Patient.objects.update_or_create(
            id=int(patient_id),
            defaults={
                "name": str(patient_name),
                "sex": sex_val(get_val(ft, "SEX", "sex")),
                "level": level,
            },
        )
        cr = ClinicalRecord.objects.create(
            patient=patient,
            age=int(float(get_val(ft, "AGE", "age", default=0) or 0)),
            bmi=to_float(get_val(ft, "BMI", "bmi")),
            sp=to_float(get_val(ft, "SP", "sp")),
            bp=to_float(get_val(ft, "BP", "bp")),
            hba1c=to_float(get_val(ft, "HbA1c", "hba1c")),
            fps=to_float(get_val(ft, "FPS", "fps")),
            pps=to_float(get_val(ft, "PPS", "pps")),
            fam_ho=str(get_val(ft, "FAMILY H/O", "fam_ho", default="")),
            on_age=to_float(get_val(ft, "ONSET AGE", "on_age")),
            dia_life=str(get_val(ft, "DIA LIFE", "dia_life", default="")),
            smk=str(get_val(ft, "SMOKING", "smk", default="")),
            phy_act=str(get_val(ft, "PHY ACT", "phy_act", default="")),
            med_use=str(get_val(ft, "MED USE", "med_use", default="")),
            med_adh=str(get_val(ft, "MED ADH", "med_adh", default="")),
            source=source,
            source_idx=source_idx,
        )
        if truth:
            ClinicalRecordLabel.objects.create(clinical_record=cr, source="mendeley_mock", **truth)
        pred = PredictionResult.objects.create(
            patient=patient,
            clinical_record=cr,
            model_name=str(res.get("model_name") or ""),
            model_version=str(res.get("model_version") or "v1"),
            risk_level=level,
            warning_message=str(res.get("warning_message") or ""),
        )
        rows = []
        for target, field in TARGETS:
            score = float(get_val(scores, target, field, default=0) or 0)
            label = int(get_val(labels, target, field, default=0) or 0)
            rows.append(
                RiskScoreDetail(
                    prediction=pred,
                    target=target,
                    risk_score=score,
                    risk_label=label,
                    risk_level=score_level(score, label),
                )
            )
        RiskScoreDetail.objects.bulk_create(rows)
        create_workflow_items(pred)
        req = None
        if endpoint:
            req = RequestLog.objects.create(
                prediction=pred,
                endpoint=endpoint,
                status_code=status_code,
                latency_ms=latency_ms,
            )
    return result_data(pred, req=req)
