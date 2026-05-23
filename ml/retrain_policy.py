from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ml.preprocessing import FT, TG, clean_data, load_data


LOGGER = logging.getLogger("ml.retrain_policy")
SKIP_CODE = 99


def env_path(name, default):
    return Path(os.environ.get(name, default))


def env_int(name, default):
    return int(os.environ.get(name, default))


def env_float(name, default):
    return float(os.environ.get(name, default))


def config_value(config, key, env_name, default):
    value = config.get(key)
    if value is not None:
        return value
    return os.environ.get(env_name, default)


def load_retrain_config():
    path = env_path(
        "AIRFLOW_RETRAIN_CONFIG_PATH",
        ROOT_DIR / "configs" / "airflow_retrain_config.json",
    )
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return {}


RETRAIN_CONFIG = load_retrain_config()
STATE_PATH = env_path("DIABETES_RETRAIN_STATE", ROOT_DIR / "ml" / "artifacts" / "retrain_state.json")
TRAINING_PATH = env_path("DIABETES_RETRAIN_TRAINING_DATA", ROOT_DIR / "data" / "training.csv")
FALLBACK_PATH = env_path("DIABETES_RETRAIN_FALLBACK_DATA", ROOT_DIR / "data" / "data.csv")
MIN_NEW_LABELS = int(config_value(RETRAIN_CONFIG, "min_new_labels", "DIABETES_RETRAIN_MIN_NEW_LABELS", 100))
MIN_NEW_RATIO = float(config_value(RETRAIN_CONFIG, "min_new_ratio", "DIABETES_RETRAIN_MIN_NEW_RATIO", 0.10))
MIN_NEW_POSITIVES = int(
    config_value(RETRAIN_CONFIG, "min_new_positives", "DIABETES_RETRAIN_MIN_NEW_POSITIVES", 20)
)
MIN_POSITIVE_TARGETS = int(
    config_value(RETRAIN_CONFIG, "min_positive_targets", "DIABETES_RETRAIN_MIN_POSITIVE_TARGETS", 2)
)
MIN_DAYS = int(config_value(RETRAIN_CONFIG, "min_days", "DIABETES_RETRAIN_MIN_DAYS", 7))
URGENT_NEW_LABELS = int(config_value(RETRAIN_CONFIG, "urgent_new_labels", "DIABETES_RETRAIN_URGENT_NEW_LABELS", 500))
MAX_MISSING_RATE = float(config_value(RETRAIN_CONFIG, "max_missing_rate", "DIABETES_RETRAIN_MAX_MISSING_RATE", 0.05))
MAX_DUPLICATE_RATE = float(
    config_value(RETRAIN_CONFIG, "max_duplicate_rate", "DIABETES_RETRAIN_MAX_DUPLICATE_RATE", 0.30)
)
FORCE_RETRAIN = bool(RETRAIN_CONFIG.get("force", False))


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
        force=True,
    )


def setup_django():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "diabetes_predict_system.settings")
    import django

    django.setup()


def now_utc():
    return datetime.now(timezone.utc)


def parse_time(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def load_state(path=STATE_PATH):
    path = Path(path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def write_state(report, path=STATE_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "last_retrain_at": now_utc().isoformat(),
        "total_labels": report["total_labels"],
        "last_label_id": report["last_label_id"],
        "training_rows": report["training_rows"],
        "positive_counts": report["positive_counts"],
    }
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state


def total_positive_counts():
    rows, total, last_id = label_rows(0)
    df = pd.DataFrame(rows)
    pos = {target: int(df[target].sum()) if target in df else 0 for target in TG}
    return pos, total, last_id


def bool_int(value):
    return int(bool(value))


def label_rows(min_id=0):
    setup_django()
    from patients.models import ClinicalRecordLabel

    labels = (
        ClinicalRecordLabel.objects.filter(id__gt=min_id)
        .select_related("clinical_record", "clinical_record__patient")
        .order_by("id")
    )
    rows = []
    for label in labels:
        rec = label.clinical_record
        patient = rec.patient
        rows.append(
            {
                "id": label.id,
                "AGE": rec.age,
                "SEX": 0 if patient.sex == "female" else 1,
                "BMI": rec.bmi,
                "SP": rec.sp,
                "BP": rec.bp,
                "HbA1c": rec.hba1c,
                "FPS": rec.fps,
                "PPS": rec.pps,
                "FAMILY H/O": rec.fam_ho,
                "ONSET AGE": rec.on_age,
                "DIA LIFE": rec.dia_life,
                "SMOKING": rec.smk,
                "PHY ACT": rec.phy_act,
                "MED USE": rec.med_use,
                "MED ADH": rec.med_adh,
                "NEP": bool_int(label.nep),
                "NEU": bool_int(label.neu),
                "RET": bool_int(label.ret),
                "CV": bool_int(label.cv),
                "PER VAS": bool_int(label.per_vas),
            }
        )
    total = ClinicalRecordLabel.objects.count()
    last_id = ClinicalRecordLabel.objects.order_by("-id").values_list("id", flat=True).first() or 0
    return rows, total, int(last_id)


def training_rows(path=TRAINING_PATH, fallback=FALLBACK_PATH):
    path = Path(path)
    fallback = Path(fallback)
    src = path if path.exists() else fallback
    if not src.exists():
        return 0
    try:
        df = clean_data(load_data(src))
    except Exception:
        return 0
    return len(df)


def quality_report(df):
    if df.empty:
        return {
            "missing_rate": 0.0,
            "duplicate_rate": 0.0,
            "schema_ok": True,
            "target_ok": True,
        }
    cols = FT + TG
    schema_ok = all(col in df.columns for col in cols)
    if not schema_ok:
        return {
            "missing_rate": 1.0,
            "duplicate_rate": 1.0,
            "schema_ok": False,
            "target_ok": False,
        }
    missing_rate = float(df[FT].isna().sum().sum() / (len(df) * len(FT)))
    duplicate_rate = float(df.duplicated(subset=cols).mean())
    target_ok = True
    for col in TG:
        vals = set(pd.to_numeric(df[col], errors="coerce").dropna().astype(int).unique().tolist())
        if not vals.issubset({0, 1}):
            target_ok = False
    return {
        "missing_rate": missing_rate,
        "duplicate_rate": duplicate_rate,
        "schema_ok": schema_ok,
        "target_ok": target_ok,
    }


def build_report(args):
    state = load_state(args.state)

    last_id = int(state.get("last_label_id") or 0)
    rows, total_labels, current_last_id = label_rows(last_id)

    df = pd.DataFrame(rows)
    pos = {target: int(df[target].sum()) if target in df else 0 for target in TG}
    pos_total = int(sum(pos.values()))
    pos_targets = int(sum(1 for value in pos.values() if value > 0))


    base_rows = int(state.get("training_rows") or training_rows(args.training_data, args.fallback_data))
    min_by_ratio = int(base_rows * args.min_new_ratio)
    min_required = min(args.min_new_labels, min_by_ratio) if min_by_ratio > 0 else args.min_new_labels
    q = quality_report(df)
    last_retrain_at = parse_time(state.get("last_retrain_at"))
    days_since = None
    if last_retrain_at:
        days_since = (now_utc() - last_retrain_at).total_seconds() / 86400

    reasons = []
    if len(df) < min_required:
        reasons.append(f"new_labeled_records={len(df)} < min_required={min_required}")
        
    if pos_total < args.min_new_positives:
        reasons.append(f"new_positive_labels={pos_total} < min_new_positives={args.min_new_positives}")
    if pos_targets < args.min_positive_targets:
        reasons.append(f"positive_targets={pos_targets} < min_positive_targets={args.min_positive_targets}")
    if not q["schema_ok"]:
        reasons.append("schema_missing_required_columns")
    if not q["target_ok"]:
        reasons.append("target_values_not_binary")
    if q["missing_rate"] > args.max_missing_rate:
        reasons.append(f"missing_rate={q['missing_rate']:.4f} > max_missing_rate={args.max_missing_rate:.4f}")
    if q["duplicate_rate"] > args.max_duplicate_rate:
        reasons.append(f"duplicate_rate={q['duplicate_rate']:.4f} > max_duplicate_rate={args.max_duplicate_rate:.4f}")
    if days_since is not None and days_since < args.min_days and len(df) < args.urgent_new_labels:
        reasons.append(f"days_since_last_retrain={days_since:.2f} < min_days={args.min_days}")

    should = args.force or not reasons
    decision = "retrain" if should else "skip"
    return {
        "decision": decision,
        "should_retrain": should,
        "forced": bool(args.force),
        "reasons": [] if should and args.force else reasons,
        "total_labels": int(total_labels),
        "last_label_id": int(current_last_id),
        "previous_last_label_id": last_id,
        "new_labeled_records": int(len(df)),
        "training_rows": int(base_rows),
        "min_required_labels": int(min_required),
        "min_new_labels": int(args.min_new_labels),
        "min_new_ratio": float(args.min_new_ratio),
        "new_positive_labels": pos_total,
        "positive_target_count": pos_targets,
        "positive_counts": pos,
        "days_since_last_retrain": None if days_since is None else round(days_since, 4),
        "quality": q,
        "state_path": str(Path(args.state)),
    }


def print_report(report):
    txt = json.dumps(report, ensure_ascii=False, indent=2)
    print(txt)
    LOGGER.info(
        "decision=%s new_labeled_records=%s positive_counts=%s days_since_last_retrain=%s reasons=%s",
        report["decision"],
        report["new_labeled_records"],
        report["positive_counts"],
        report["days_since_last_retrain"],
        report["reasons"],
    )


def check(args):
    report = build_report(args)
    print_report(report)
    return 0 if report["should_retrain"] else SKIP_CODE


def mark_success(args):
    report = build_report(args)
    pos, total, last_id = total_positive_counts()
    report["positive_counts"] = pos
    report["total_labels"] = total
    report["last_label_id"] = last_id
    report["training_rows"] = training_rows(args.training_data, args.fallback_data)
    state = write_state(report, args.state)
    print(json.dumps({"saved": True, "state": state}, ensure_ascii=False, indent=2))
    return 0


def parser():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ["check", "mark-success"]:
        s = sub.add_parser(name)
        s.add_argument("--state", default=str(STATE_PATH))
        s.add_argument("--training-data", default=str(TRAINING_PATH))
        s.add_argument("--fallback-data", default=str(FALLBACK_PATH))
        s.add_argument("--min-new-labels", type=int, default=MIN_NEW_LABELS)
        s.add_argument("--min-new-ratio", type=float, default=MIN_NEW_RATIO)
        s.add_argument("--min-new-positives", type=int, default=MIN_NEW_POSITIVES)
        s.add_argument("--min-positive-targets", type=int, default=MIN_POSITIVE_TARGETS)
        s.add_argument("--min-days", type=int, default=MIN_DAYS)
        s.add_argument("--urgent-new-labels", type=int, default=URGENT_NEW_LABELS)
        s.add_argument("--max-missing-rate", type=float, default=MAX_MISSING_RATE)
        s.add_argument("--max-duplicate-rate", type=float, default=MAX_DUPLICATE_RATE)
        s.add_argument("--force", action="store_true", default=FORCE_RETRAIN)
    return p


if __name__ == "__main__":
    configure_logging()
    args = parser().parse_args()
    if args.cmd == "check":
        raise SystemExit(check(args))
    raise SystemExit(mark_success(args))
