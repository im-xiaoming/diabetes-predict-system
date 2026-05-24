import re

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


COLS = {
    "sl_no": "SL.NO",
    "name": "NAME",
    "age": "AGE",
    "sex": "SEX",
    "bmi": "BMI",
    "sp": "SP",
    "bp": "BP",
    "hba1c": "HbA1c",
    "fps": "FPS",
    "pps": "PPS",
    "fam_ho": "FAMILY H/O",
    "on_age": "ONSET AGE",
    "dia_life": "DIA LIFE",
    "smk": "SMOKING",
    "phy_act": "PHY ACT",
    "med_use": "MED USE",
    "med_adh": "MED ADH",
    "nep": "NEP",
    "neu": "NEU",
    "ret": "RET",
    "cv": "CV",
    "per_vas": "PER VAS",
}

FT = [
    "AGE",
    "SEX",
    "BMI",
    "SP",
    "BP",
    "HbA1c",
    "FPS",
    "PPS",
    "FAMILY H/O",
    "ONSET AGE",
    "DIA LIFE",
    "SMOKING",
    "PHY ACT",
    "MED USE",
    "MED ADH",
]
TG = ["NEP", "NEU", "RET", "CV", "PER VAS"]
NUM = ["AGE", "BMI", "SP", "BP", "HbA1c", "FPS", "PPS", "ONSET AGE", "DIA LIFE"]
CAT = ["SEX", "FAMILY H/O", "SMOKING", "PHY ACT", "MED USE", "MED ADH"]


def rename_cols(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df.rename(columns=COLS)


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


def load_data_spark(path):
    try:
        from pyspark.sql import SparkSession
        from pyspark.sql import functions as F
    except ImportError as exc:
        raise RuntimeError(
            "PySpark backend requested but pyspark is not installed. "
            "Install it with: python -m pip install pyspark"
        ) from exc

    spark = (
        SparkSession.builder.appName("diabetes-preprocessing")
        .config("spark.sql.execution.arrow.pyspark.enabled", "true")
        .getOrCreate()
    )
    try:
        sdf = spark.read.option("header", True).option("inferSchema", False).csv(str(path))
        for col_name in sdf.columns:
            stripped = col_name.strip()
            if stripped != col_name:
                sdf = sdf.withColumnRenamed(col_name, stripped)

        for old, new in COLS.items():
            if old in sdf.columns and old != new:
                sdf = sdf.withColumnRenamed(old, new)

        raw_n = sdf.count()

        dia_life_str = F.lower(F.trim(F.col("DIA LIFE").cast("string")))
        dia_life_num = F.regexp_extract(dia_life_str, r"-?\d+(\.\d+)?", 0).cast("double")
        sdf = sdf.withColumn(
            "DIA LIFE",
            F.when(dia_life_str.contains("month"), dia_life_num / F.lit(12.0)).otherwise(dia_life_num),
        )

        for col_name in NUM:
            sdf = sdf.withColumn(col_name, F.col(col_name).cast("double"))
        for col_name in CAT:
            sdf = sdf.withColumn(col_name, F.trim(F.col(col_name).cast("string")))
        for col_name in TG:
            sdf = sdf.withColumn(col_name, F.col(col_name).cast("int"))

        sdf = sdf.dropna(subset=TG).dropDuplicates(FT + TG)
        return sdf.select(*(FT + TG)).toPandas().reset_index(drop=True), raw_n
    finally:
        spark.stop()


def clean_data(df):
    df = rename_cols(df)
    df = df.copy()
    df["DIA LIFE"] = df["DIA LIFE"].apply(parse_dia_life)
    for c in NUM:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in CAT:
        df[c] = df[c].astype("string").str.strip()
    for c in TG:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=TG)
    df[TG] = df[TG].astype(int)
    df = df.drop_duplicates(subset=FT + TG).reset_index(drop=True)
    return df


def load_clean_data(path, backend="pandas"):
    backend = (backend or "pandas").strip().lower()
    if backend == "pandas":
        df = load_data(path)
        raw_n = len(df)
        return clean_data(df), raw_n
    if backend in {"spark", "pyspark"}:
        return load_data_spark(path)
    raise ValueError(f"Unsupported preprocessing backend: {backend}")


def split_xy(df):
    x = df[FT].copy()
    y = df[TG].copy()
    return x, y, FT, TG, NUM, CAT


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
            ("num", num_pipe, NUM),
            ("cat", cat_pipe, CAT),
        ]
    )
