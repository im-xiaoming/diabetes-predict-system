from django.db import models


class PredictionResult(models.Model):
    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="predictions")
    clinical_record = models.ForeignKey("patients.ClinicalRecord", on_delete=models.CASCADE, related_name="predictions")
    model_name = models.CharField(max_length=100)
    model_version = models.CharField(max_length=50)
    risk_level = models.CharField(max_length=20)
    warning_message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.id} - {self.model_name} - {self.created_at}"


class RiskScoreDetail(models.Model):
    """Prediction results."""
    prediction = models.ForeignKey(PredictionResult, on_delete=models.CASCADE, related_name="scores")
    target = models.CharField(max_length=20)
    risk_score = models.FloatField()
    risk_label = models.PositiveSmallIntegerField()
    risk_level = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.prediction_id} - {self.target}"


class RequestLog(models.Model):
    prediction = models.ForeignKey(PredictionResult, on_delete=models.CASCADE, related_name="request_logs")
    endpoint = models.CharField(max_length=100)
    status_code = models.PositiveIntegerField()
    latency_ms = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.endpoint} - {self.status_code} - {self.created_at}"
