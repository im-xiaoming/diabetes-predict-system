from pathlib import Path

import yaml
from django.conf import settings
from django.db import connection, transaction
from tools import AttrDict


TARGET = ["CV", "PER VAS", "NEP", "NEU", "RET"]

LEVEL_MAP = {
    "Thấp": "low",
    "Trung bình": "medium",
    "Cao": "high",
    "Rất cao": "high",
}

SEX_MAP = {0: "female", 1: "male"}


def get_pandas():
    import pandas as pd

    return pd


def get_preprocessing_helpers():
    from ml.preprocessing import parse_dia_life, rename_cols

    return parse_dia_life, rename_cols


def calculate_diabetes_risk(row):
    with open(Path(settings.BASE_DIR) / "configs" / "weights.yaml", "r", encoding="utf-8") as file:
        weights = AttrDict(yaml.safe_load(file))

    score = (
        row["CV"] * weights.CV
        + row["PER VAS"] * weights.PER_VAS
        + row["NEP"] * weights.NEP
        + row["NEU"] * weights.NEU
        + row["RET"] * weights.RET
    )

    if score == 0:
        return "Thấp", 0
    if 1 <= score <= 2:
        return "Trung bình", 1
    if 3 <= score <= 5:
        return "Cao", 2
    return "Rất cao", 3


def calculate_diabetes_risks(data):
    pd = get_pandas()
    results = data[TARGET].apply(calculate_diabetes_risk, axis=1, result_type="expand")
    results.columns = ["LV", "WAR"]
    return pd.concat([data, results], axis=1)


def to_float(value):
    pd = get_pandas()
    if pd.isna(value) or value == "":
        return 0.0
    return float(value)


def to_int(value):
    pd = get_pandas()
    if pd.isna(value) or value == "":
        return 0
    return int(float(value))


def sex(value):
    pd = get_pandas()
    if pd.isna(value):
        return "male"
    normalized = str(value).strip().lower()
    if normalized in {"0", "female", "f", "nu", "nữ"}:
        return "female"
    if normalized in {"1", "male", "m", "nam"}:
        return "male"
    return SEX_MAP.get(to_int(value), "male")


def process_csv_to_database(csv_path):
    """Import labeled training/evaluation CSV into Patient, ClinicalRecord, and ClinicalRecordLabel.

    This path stores ground-truth labels only. It does not create PredictionResult rows.
    PredictionResult rows are created by Mock HIS / HIS Inference after calling the model API.
    """
    from patients.models import ClinicalRecord, ClinicalRecordLabel, Patient

    try:
        pd = get_pandas()
        parse_dia_life, rename_cols = get_preprocessing_helpers()
        data = rename_cols(pd.read_csv(csv_path))
        required = [
            "SL.NO",
            "NAME",
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
            *TARGET,
        ]
        data = data.dropna(subset=[column for column in required if column in data.columns])
        data = data.drop_duplicates()
        data["DIA LIFE"] = data["DIA LIFE"].apply(parse_dia_life)
        for column in TARGET:
            data[column] = pd.to_numeric(data[column], errors="coerce").fillna(0).astype(int)
        data = calculate_diabetes_risks(data)

        saved = 0
        with transaction.atomic():
            for _, row in data.iterrows():
                patient, _ = Patient.objects.update_or_create(
                    id=to_int(row["SL.NO"]),
                    defaults={
                        "name": str(row["NAME"]),
                        "sex": sex(row["SEX"]),
                        "level": LEVEL_MAP.get(row["LV"], "low"),
                    },
                )
                clinical_record = ClinicalRecord.objects.create(
                    patient=patient,
                    age=to_int(row["AGE"]),
                    bmi=to_float(row["BMI"]),
                    sp=to_float(row["SP"]),
                    bp=to_float(row["BP"]),
                    hba1c=to_float(row["HbA1c"]),
                    fps=to_float(row["FPS"]),
                    pps=to_float(row["PPS"]),
                    fam_ho=str(row["FAMILY H/O"]),
                    on_age=to_float(row["ONSET AGE"]),
                    dia_life=str(row["DIA LIFE"]),
                    smk=str(row["SMOKING"]),
                    phy_act=str(row["PHY ACT"]),
                    med_use=str(row["MED USE"]),
                    med_adh=str(row["MED ADH"]),
                    source="uploaded_labeled_csv",
                )
                ClinicalRecordLabel.objects.create(
                    clinical_record=clinical_record,
                    nep=bool(to_int(row["NEP"])),
                    neu=bool(to_int(row["NEU"])),
                    ret=bool(to_int(row["RET"])),
                    cv=bool(to_int(row["CV"])),
                    per_vas=bool(to_int(row["PER VAS"])),
                    source="uploaded_label",
                )
                saved += 1

        return saved
    finally:
        connection.close()
