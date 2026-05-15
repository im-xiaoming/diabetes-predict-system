from pathlib import Path
import sys

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ml.preprocessing import rename_cols


DATA_PATH = ROOT_DIR / "data" / "data.csv"
FT = [
    "age",
    "sex",
    "bmi",
    "sp",
    "bp",
    "hba1c",
    "fps",
    "pps",
    "fam_ho",
    "on_age",
    "dia_life",
    "smk",
    "phy_act",
    "med_use",
    "med_adh",
]


def native(v):
    if pd.isna(v):
        return None
    if hasattr(v, "item"):
        return v.item()
    return v


def load_samples(path=DATA_PATH, count=1):
    df = pd.read_csv(path)
    df = rename_cols(df)
    rows = df[FT].head(count).to_dict(orient="records")
    return [{k: native(v) for k, v in row.items()} for row in rows]
