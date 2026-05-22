from django.db import models


class AlertLevel(models.TextChoices):
    HIGH = "high", "High"


class AlertStatus(models.TextChoices):
    NEW = "new", "New"
    ACKNOWLEDGED = "acknowledged", "Acknowledged"
    WATCHING = "watching", "Watching"
    RESOLVED = "resolved", "Resolved"


class Alert(models.Model):
    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="alerts")
    prediction = models.ForeignKey("predictions.PredictionResult", on_delete=models.CASCADE, related_name="alerts")
    score = models.OneToOneField("predictions.RiskScoreDetail", on_delete=models.CASCADE, related_name="alert")
    target = models.CharField(max_length=20)
    level = models.CharField(max_length=20, choices=AlertLevel.choices)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=AlertStatus.choices, default=AlertStatus.NEW)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    doctor_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"AL-{self.id} {self.patient_id} {self.target}"


class WatchlistStatus(models.TextChoices):
    OPEN = "open", "Open"
    REVIEWED = "reviewed", "Reviewed"


class WatchlistItem(models.Model):
    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="watchlist_items")
    prediction = models.ForeignKey("predictions.PredictionResult", on_delete=models.CASCADE, related_name="watchlist_items")
    score = models.OneToOneField("predictions.RiskScoreDetail", on_delete=models.CASCADE, related_name="watchlist_item")
    target = models.CharField(max_length=20)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=WatchlistStatus.choices, default=WatchlistStatus.OPEN)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    doctor_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"WL-{self.id} {self.patient_id} {self.target}"
