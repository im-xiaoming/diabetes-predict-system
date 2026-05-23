from pathlib import Path
import os
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import joblib
import pandas as pd

from ml.preprocessing import COLS, parse_dia_life


MODEL_PATH = Path(os.environ.get("MODEL_PATH", ROOT_DIR / "ml" / "artifacts" / "model.pkl"))


def load_model():
    return joblib.load(MODEL_PATH)


def risk_level(labels):
    n = sum(int(v) for v in labels.values())
    if n >= 2:
        return "high"
    if n == 1:
        return "medium"
    return "low"


def warning_message(level):
    msg = {
        "high": "Bệnh nhân có nguy cơ cao, cần ưu tiên theo dõi.",
        "medium": "Bệnh nhân có nguy cơ trung bình, cần theo dõi thêm.",
        "low": "Bệnh nhân có nguy cơ thấp.",
    }
    return msg[level]


def get_scores(mdl, x, tg):
    out = {}
    est = mdl.named_steps["mdl"].estimators_
    pp = mdl.named_steps["pp"]
    xt = pp.transform(x)
    for t, e in zip(tg, est):
        if hasattr(e, "predict_proba"):
            p = e.predict_proba(xt)[0]
            out[t] = float(p[1]) if len(p) > 1 else float(p[0])
        else:
            out[t] = float(e.predict(xt)[0])
    return out


def build_row(data, ft):
    data = dict(data)
    rev = {v: k for k, v in COLS.items()}
    row = {}
    for c in ft:
        if c in data:
            row[c] = data[c]
        elif c in COLS and COLS[c] in data:
            row[c] = data[COLS[c]]
        elif c in rev and rev[c] in data:
            row[c] = data[rev[c]]
        else:
            row[c] = None
    dia = "DIA LIFE" if "DIA LIFE" in row else "dia_life"
    if dia in row:
        row[dia] = parse_dia_life(row.get(dia))
    return row


def predict_one(data):
    bundle = load_model()
    ft = bundle["features"]
    tg = bundle["targets"]
    mdl = bundle["model"]
    row = build_row(data, ft)
    x = pd.DataFrame([row], columns=ft)
    pred = mdl.predict(x)[0]
    labels = {t: int(v) for t, v in zip(tg, pred)}
    scores = get_scores(mdl, x, tg)
    level = risk_level(labels)
    return {
        "risk_scores": scores,
        "risk_labels": labels,
        "risk_level": level,
        "warning_message": warning_message(level),
        "model_name": bundle["model_name"],
        "model_version": "v1",
    }
