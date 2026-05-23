from __future__ import annotations

from pathlib import Path
import random
import sys

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ml.preprocessing import FT, TG


DEFAULT_TOTAL = 10000
PATIENT_ID_START = 1_000_000
SEED = 20260523


def native(v):
    if pd.isna(v):
        return None
    if hasattr(v, "item"):
        return v.item()
    return v


def total_records(path=None):
    return DEFAULT_TOTAL


def complete(row):
    vals = [row.get(k) for k in FT]
    ok = sum(0 if pd.isna(v) else 1 for v in vals)
    return round(ok / len(FT) * 100)


def _rng(idx):
    return random.Random(SEED + int(idx))


def _round(value, digits=2):
    return round(float(value), digits)


def _target_labels(payload):
    age = float(payload["AGE"])
    bmi = float(payload["BMI"])
    hba1c = float(payload["HbA1c"])
    fps = float(payload["FPS"])
    pps = float(payload["PPS"])
    bp = float(payload["BP"])
    dia_life = float(payload["DIA LIFE"])
    smk = int(payload["SMOKING"])
    med_adh = int(payload["MED ADH"])

    return {
        "NEP": int(hba1c >= 8.4 or fps >= 170 or dia_life >= 8),
        "NEU": int(age >= 52 or dia_life >= 10 or pps >= 260),
        "RET": int(hba1c >= 8.8 or pps >= 300 or dia_life >= 12),
        "CV": int(bp >= 92 or bmi >= 31 or smk == 2 or age >= 58),
        "PER VAS": int((smk == 2 and age >= 62) or (med_adh == 0 and hba1c >= 10.5)),
    }


def generate_payload(idx):
    rng = _rng(idx)
    offset = int(idx) + 1
    age = 24 + (offset * 7) % 55
    onset_age = max(18, age - (1 + (offset * 5) % 22))
    dia_life = _round(max(0.1, age - onset_age + ((offset % 17) / 100)), 2)
    bmi = _round(18.0 + ((offset * 137) % 2400) / 100 + rng.random() / 1000, 3)
    sp = 95 + (offset * 11) % 76
    bp = 60 + (offset * 7) % 46
    hba1c = _round(5.2 + ((offset * 19) % 850) / 100 + rng.random() / 1000, 3)
    fps = _round(80 + (offset * 23) % 270 + rng.random() / 1000, 3)
    pps = _round(fps + 45 + (offset * 31) % 210 + rng.random() / 1000, 3)

    return {
        "AGE": age,
        "SEX": offset % 2,
        "BMI": bmi,
        "SP": sp,
        "BP": bp,
        "HbA1c": hba1c,
        "FPS": fps,
        "PPS": pps,
        "FAMILY H/O": (offset // 2) % 2,
        "ONSET AGE": onset_age,
        "DIA LIFE": dia_life,
        "SMOKING": (offset * 3) % 3,
        "PHY ACT": (offset * 5) % 2,
        "MED USE": 1 if offset % 7 else 0,
        "MED ADH": (offset * 11) % 3,
    }


def make_record(row, idx):
    payload = {k: native(row.get(k)) for k in FT}
    truth = {k: native(row.get(k)) for k in TG}
    pid = native(row.get("SL.NO")) or PATIENT_ID_START + idx
    name = native(row.get("NAME")) or f"Mock Patient {idx + 1:05d}"
    pct = complete(row)
    return {
        "idx": idx,
        "pid": pid,
        "name": name,
        "complete": pct,
        "ready": pct == 100,
        "payload": payload,
        "truth": truth,
    }


def generate_record(idx):
    payload = generate_payload(idx)
    row = {
        "SL.NO": PATIENT_ID_START + idx,
        "NAME": f"Mock Patient {idx + 1:05d}",
        **payload,
        **_target_labels(payload),
    }
    return make_record(row, idx)


def load_samples(path=None, count=1):
    return [generate_record(idx)["payload"] for idx in range(max(0, int(count)))]


def load_records(path=None, count=20, offset=0, limit=None):
    if limit is None:
        limit = count
    offset = max(0, int(offset))
    limit = max(0, int(limit))
    total = total_records()
    end = min(total, offset + limit)
    return [generate_record(idx) for idx in range(offset, end)]


def load_record(idx, path=None):
    idx = int(idx)
    if idx < 0 or idx >= total_records():
        return None
    return generate_record(idx)
