from unittest.mock import patch

from django.test import TestCase

from api.schemas import IngestRequest
from patients.models import ClinicalRecord, ClinicalRecordLabel, Patient

from .models import PredictionResult, RequestLog, RiskScoreDetail
from .services import save_prediction


FEATURES = {
    "AGE": 58,
    "SEX": "female",
    "BMI": 29.1,
    "SP": 138,
    "BP": 88,
    "HbA1c": 8.4,
    "FPS": 170,
    "PPS": 240,
    "FAMILY H/O": "1",
    "ONSET AGE": 49,
    "DIA LIFE": "9",
    "SMOKING": "0",
    "PHY ACT": "1",
    "MED USE": "1",
    "MED ADH": "1",
}

RESULT = {
    "risk_scores": {"NEP": 0.88, "NEU": 0.61, "RET": 0.2, "CV": 0.1, "PER VAS": 0.05},
    "risk_labels": {"NEP": 1, "NEU": 1, "RET": 0, "CV": 0, "PER VAS": 0},
    "risk_level": "high",
    "warning_message": "watch",
    "model_name": "rf",
    "model_version": "v1",
}


class PredictionSaveTests(TestCase):
    def test_save_prediction_persists_history_truth_and_workflow(self):
        out = save_prediction(
            patient_id=18,
            patient_name="Patient 18",
            ft=FEATURES,
            res=RESULT,
            source="mock_his",
            source_idx=3,
            truth={"NEP": 1, "NEU": 0, "RET": 0, "CV": 1, "PER VAS": 0},
            endpoint="/api/ingest/",
            status_code=200,
            latency_ms=12.4,
        )

        self.assertTrue(out["saved"])
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(ClinicalRecord.objects.count(), 1)
        self.assertEqual(ClinicalRecordLabel.objects.count(), 1)
        self.assertEqual(PredictionResult.objects.count(), 1)
        self.assertEqual(RiskScoreDetail.objects.count(), 5)
        self.assertEqual(RequestLog.objects.count(), 1)
        self.assertEqual(len(out["alert_ids"]), 1)
        self.assertEqual(len(out["watchlist_ids"]), 1)

        again = save_prediction(
            patient_id=18,
            patient_name="Patient 18",
            ft=FEATURES,
            res=RESULT,
            source="mock_his",
            source_idx=3,
        )
        self.assertTrue(again["already_saved"])
        self.assertEqual(PredictionResult.objects.count(), 1)


class IngestApiTests(TestCase):
    def test_ingest_route_uses_prediction_and_persists_result(self):
        from api import main

        req = IngestRequest(
            patient_id=21,
            patient_name="Patient 21",
            source="his",
            **FEATURES,
        )
        with patch.object(main, "MODEL_PATH") as mdl, patch.object(main, "predict_one", return_value=RESULT):
            mdl.exists.return_value = True
            out = main.ingest(req)

        self.assertTrue(out["saved"])
        self.assertEqual(out["patient_id"], 21)
        self.assertEqual(PredictionResult.objects.count(), 1)
