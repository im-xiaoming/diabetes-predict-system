import re

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def rename_cols(df):
    cols = {
        "SL.NO": "sl_no",
        "NAME": "name",
        "AGE": "age",
        "SEX": "sex",
        "BMI": "bmi",
        "SP": "sp",
        "BP": "bp",
        "HbA1c": "hba1c",
        "FPS": "fps",
        "PPS": "pps",
        "FAMILY H/O": "fam_ho",
        "ONSET AGE": "on_age",
        "DIA LIFE": "dia_life",
        "SMOKING": "smk",
        "PHY ACT": "phy_act",
        "MED USE": "med_use",
        "MED ADH": "med_adh",
        "NEP": "nep",
        "NEU": "neu",
        "RET": "ret",
        "CV": "cv",
        "PER VAS": "per_vas",
    }
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df.rename(columns=cols)


def parse_dia_life(v):
    if pd.isna(v):
        return np.nan
    s = str(v).strip().lower()
    m = re.search(r"-?\d+(\.\d+)?", s)
    if not m:
        return np.nan
    n = float(m.group())
    if "month" in s:
        return n / 12
    return n


def load_data(path):
    df = pd.read_csv(path)
    return rename_cols(df)


def clean_data(df):
    df = rename_cols(df)
    ft = [
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
    tg = ["nep", "neu", "ret", "cv", "per_vas"]
    num = ["age", "bmi", "sp", "bp", "hba1c", "fps", "pps", "on_age", "dia_life"]
    cat = ["sex", "fam_ho", "smk", "phy_act", "med_use", "med_adh"]
    df = df.copy()
    df["dia_life"] = df["dia_life"].apply(parse_dia_life)
    for c in num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in cat:
        df[c] = df[c].astype("string").str.strip()
    for c in tg:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=tg)
    df[tg] = df[tg].astype(int)
    df = df.drop_duplicates(subset=ft + tg).reset_index(drop=True)
    return df


def split_xy(df):
    ft = [
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
    tg = ["nep", "neu", "ret", "cv", "per_vas"]
    num = ["age", "bmi", "sp", "bp", "hba1c", "fps", "pps", "on_age", "dia_life"]
    cat = ["sex", "fam_ho", "smk", "phy_act", "med_use", "med_adh"]
    x = df[ft].copy()
    y = df[tg].copy()
    return x, y, ft, tg, num, cat


def build_preprocessor():
    num_pipe = Pipeline(
        [
            ("imp", SimpleImputer(strategy="median")),
            ("sc", StandardScaler()),
        ]
    )
    try:
        enc = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        enc = OneHotEncoder(handle_unknown="ignore", sparse=False)
    cat_pipe = Pipeline(
        [
            ("imp", SimpleImputer(strategy="most_frequent")),
            ("enc", enc),
        ]
    )
    return ColumnTransformer(
        [
            ("num", num_pipe, ["age", "bmi", "sp", "bp", "hba1c", "fps", "pps", "on_age", "dia_life"]),
            ("cat", cat_pipe, ["sex", "fam_ho", "smk", "phy_act", "med_use", "med_adh"]),
        ]
    )
