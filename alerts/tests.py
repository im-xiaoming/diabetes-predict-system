from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from patients.models import ClinicalRecord, Patient
from predictions.models import PredictionResult, RiskScoreDetail

from .models import Alert, AlertStatus, WatchlistItem, WatchlistStatus
from .services import create_workflow_items


class AlertWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="doctor", password="pass12345")
        self.patient = Patient.objects.create(id=7, name="Patient 7", sex="female", level="high")
        self.record = ClinicalRecord.objects.create(
            patient=self.patient,
            age=61,
            bmi=28.2,
            sp=140,
            bp=90,
            hba1c=8.1,
            fps=160,
            pps=230,
            fam_ho="1",
            on_age=52,
            dia_life="9",
            smk="0",
            phy_act="1",
            med_use="1",
            med_adh="1",
            source="test",
        )
        self.pred = PredictionResult.objects.create(
            patient=self.patient,
            clinical_record=self.record,
            model_name="rf",
            model_version="v1",
            risk_level="high",
            warning_message="watch",
        )
        self.high = RiskScoreDetail.objects.create(
            prediction=self.pred,
            target="NEP",
            risk_score=0.91,
            risk_label=1,
            risk_level="high",
        )
        self.medium = RiskScoreDetail.objects.create(
            prediction=self.pred,
            target="CV",
            risk_score=0.61,
            risk_label=1,
            risk_level="medium",
        )
        RiskScoreDetail.objects.create(
            prediction=self.pred,
            target="RET",
            risk_score=0.22,
            risk_label=0,
            risk_level="low",
        )

    def test_policy_splits_alert_and_watchlist(self):
        rows = create_workflow_items(self.pred)
        again = create_workflow_items(self.pred)

        self.assertEqual(len(rows["alerts"]), 1)
        self.assertEqual(len(rows["watchlist"]), 1)
        self.assertEqual(Alert.objects.count(), 1)
        self.assertEqual(WatchlistItem.objects.count(), 1)
        self.assertEqual(len(again["alerts"]), 0)
        self.assertEqual(len(again["watchlist"]), 0)
        self.assertEqual(Alert.objects.get().score, self.high)
        self.assertEqual(WatchlistItem.objects.get().score, self.medium)

    def test_doctor_can_acknowledge_note_and_resolve_alert(self):
        create_workflow_items(self.pred)
        alert = Alert.objects.get()
        self.client.force_login(self.user)

        self.client.post(
            reverse("alert-status", args=[alert.id]),
            {"status": AlertStatus.ACKNOWLEDGED, "doctor_note": "Đã xem hồ sơ."},
        )
        alert.refresh_from_db()
        self.assertEqual(alert.status, AlertStatus.ACKNOWLEDGED)
        self.assertIsNotNone(alert.acknowledged_at)
        self.assertEqual(alert.doctor_note, "Đã xem hồ sơ.")

        self.client.post(
            reverse("alert-status", args=[alert.id]),
            {"status": AlertStatus.RESOLVED, "doctor_note": "Đã theo dõi và xử lý."},
        )
        alert.refresh_from_db()
        self.assertEqual(alert.status, AlertStatus.RESOLVED)
        self.assertIsNotNone(alert.resolved_at)

    def test_watchlist_page_filters_patient_target_and_status(self):
        create_workflow_items(self.pred)
        other = Patient.objects.create(id=9, name="Other Patient", sex="male", level="medium")
        record = ClinicalRecord.objects.create(
            patient=other,
            age=54,
            bmi=25.4,
            sp=130,
            bp=80,
            hba1c=7.2,
            fps=145,
            pps=210,
            fam_ho="0",
            on_age=47,
            dia_life="7",
            smk="0",
            phy_act="1",
            med_use="1",
            med_adh="1",
            source="test",
        )
        pred = PredictionResult.objects.create(
            patient=other,
            clinical_record=record,
            model_name="rf",
            model_version="v1",
            risk_level="medium",
            warning_message="watch",
        )
        score = RiskScoreDetail.objects.create(
            prediction=pred,
            target="NEU",
            risk_score=0.59,
            risk_label=1,
            risk_level="medium",
        )
        WatchlistItem.objects.create(
            patient=other,
            prediction=pred,
            score=score,
            target="NEU",
            message="reviewed",
            status=WatchlistStatus.REVIEWED,
        )
        self.client.force_login(self.user)

        res = self.client.get(reverse("watchlist"), {"q": "Patient 7", "target": "CV", "status": "open"})

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["paginator"].count, 1)
        self.assertContains(res, "Patient 7")
        self.assertNotContains(res, "Other Patient")

    def test_watchlist_page_paginates_twenty_rows(self):
        create_workflow_items(self.pred)
        for idx in range(20):
            score = RiskScoreDetail.objects.create(
                prediction=self.pred,
                target=f"CV {idx}",
                risk_score=0.58,
                risk_label=1,
                risk_level="medium",
            )
            WatchlistItem.objects.create(
                patient=self.patient,
                prediction=self.pred,
                score=score,
                target="CV",
                message=f"watch {idx}",
            )
        self.client.force_login(self.user)

        res = self.client.get(reverse("watchlist"))

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["paginator"].count, 21)
        self.assertEqual(len(res.context["watchlist"]), 20)

    def test_doctor_can_review_and_reopen_watchlist(self):
        create_workflow_items(self.pred)
        item = WatchlistItem.objects.get()
        self.client.force_login(self.user)

        self.client.post(
            reverse("watchlist-status", args=[item.id]),
            {"status": WatchlistStatus.REVIEWED, "doctor_note": "Đã rà soát hồ sơ."},
        )
        item.refresh_from_db()
        self.assertEqual(item.status, WatchlistStatus.REVIEWED)
        self.assertIsNotNone(item.reviewed_at)
        self.assertEqual(item.doctor_note, "Đã rà soát hồ sơ.")

        self.client.post(
            reverse("watchlist-status", args=[item.id]),
            {"status": WatchlistStatus.OPEN, "doctor_note": "Cần theo dõi lại."},
        )
        item.refresh_from_db()
        self.assertEqual(item.status, WatchlistStatus.OPEN)
        self.assertIsNone(item.reviewed_at)
        self.assertEqual(item.doctor_note, "Cần theo dõi lại.")
