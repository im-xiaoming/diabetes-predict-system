import pandas as pd
import yaml
from django.conf import settings
from django.db import transaction, connection
from pathlib import Path
from tools import AttrDict

TARGET = ['CV', 'PER VAS', 'NEP', 'NEU', 'RET']

LEVEL_MAP = {
    'Thấp': 'low',
    'Trung bình': 'medium',
    'Cao': 'high',
    'Rất cao': 'very_high',
}

SEX_MAP = {0: 'female', 1: 'male'}

def calculate_diabetes_risk(row):
    with open(Path(settings.BASE_DIR) / 'configs' / 'weights.yaml', 'r', encoding='utf-8') as file:
        weights = yaml.safe_load(file)

    weights = AttrDict(weights)

    score = (row['CV'] * weights.CV +
             row['PER VAS'] * weights.PER_VAS +
             row['NEP'] * weights.NEP +
             row['NEU'] * weights.NEU +
             row['RET'] * weights.RET)

    if score == 0:
        return 'Thấp', 0
    elif 1 <= score <= 2:
        return 'Trung bình', 1
    elif 3 <= score <= 5:
        return 'Cao', 2
    else:
        return 'Rất cao', 3


def calculate_diabetes_risks(data):
    results = data[TARGET].apply(calculate_diabetes_risk, axis=1, result_type='expand')
    results.columns = ['LV', 'WAR']
    data = pd.concat([data, results], axis=1)
    return data


def process_csv_to_database(csv_path):
    """Đọc CSV, tính toán mức nguy cơ, và lưu danh sách Patient vào DB."""
    from patients.models import Patient, PatientTargetFeatures

    try:
        data = pd.read_csv(csv_path)
        data.rename({'SL.NO': 'SL_NO'}, axis=1, inplace=True)
        data = calculate_diabetes_risks(data)

        patients = [
            Patient(
                id=int(row['SL_NO']),
                name=str(row['NAME']),
                age=int(row['AGE']),
                sex=SEX_MAP.get(int(row['SEX']), 'male'),
                level=LEVEL_MAP.get(row['LV'], 'low'),
            )
            for _, row in data.iterrows()
        ]

        features = [
            PatientTargetFeatures(
                patient_id=int(row['SL_NO']),
                nep=bool(int(row['NEP'])),
                neu=bool(int(row['NEU'])),
                ret=bool(int(row['RET'])),
                cv=bool(int(row['CV'])),
                per_vas=bool(int(row['PER VAS'])),
            )
            for _, row in data.iterrows()
        ]

        with transaction.atomic():
            Patient.objects.bulk_create(patients, ignore_conflicts=True)
            existing = set(
                PatientTargetFeatures.objects
                    .filter(patient_id__in=[f.patient_id for f in features])
                    .values_list('patient_id', flat=True)
            )
            new_features = [f for f in features if f.patient_id not in existing]
            PatientTargetFeatures.objects.bulk_create(new_features)

        return len(patients)
    finally:
        connection.close()
