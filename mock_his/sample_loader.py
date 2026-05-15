from pathlib import Path
import sys

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ml.preprocessing import FT, rename_cols


DATA_PATH = ROOT_DIR / "data" / "data.csv"
META = ["SL.NO", "NAME"]


def native(v):
    if pd.isna(v):
        return None
    if hasattr(v, "item"):
        return v.item()
    return v


def complete(row):
    vals = [row.get(k) for k in FT]
    ok = sum(0 if pd.isna(v) else 1 for v in vals)
    return round(ok / len(FT) * 100)


def make_record(row, idx):
    payload = {k: native(row.get(k)) for k in FT}
    pid = native(row.get("SL.NO")) or idx + 1
    name = native(row.get("NAME")) or f"Patient {pid}"
    pct = complete(row)
    return {
        "idx": idx,
        "pid": pid,
        "name": name,
        "complete": pct,
        "ready": pct == 100,
        "payload": payload,
    }


def total_records(path=DATA_PATH):
    return sum(1 for _ in open(path, encoding="utf-8")) - 1


def load_samples(path=DATA_PATH, count=1):
    df = pd.read_csv(path)
    df = rename_cols(df)
    rows = df[FT].head(count).to_dict(orient="records")
    return [{k: native(v) for k, v in row.items()} for row in rows]


def load_records(path=DATA_PATH, count=20, offset=0, limit=None):
    if limit is None:
        limit = count
    df = pd.read_csv(path)
    df = rename_cols(df)
    cols = [c for c in META + FT if c in df.columns]
    rows = df[cols].iloc[offset:offset + limit].to_dict(orient="records")
    out = []
    for idx, row in enumerate(rows):
        out.append(make_record(row, offset + idx))
    return out


def load_record(idx, path=DATA_PATH):
    rows = load_records(path=path, offset=idx, limit=1)
    if not rows:
        return None
    return rows[0]
