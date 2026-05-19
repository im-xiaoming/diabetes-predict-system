from django.db import models


class Sex(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"


class Level(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    VERY_HIGH = "very_high", "Very high"


class Patient(models.Model):
    """Master patient profile.

    Clinical measurements and model outputs are stored in separate tables so a
    patient can have many incoming HIS records and prediction results.
    """

    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=50)
    age = models.PositiveIntegerField()
    sex = models.TextField(choices=Sex.choices)
    level = models.TextField(choices=Level.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def war(self):
        if self.level == "low":
            return 0
        if self.level == "medium":
            return 1
        if self.level == "high":
            return 2
        return 3

    def __str__(self):
        return f"{self.id} - {self.name}"


class ClinicalRecord(models.Model):
    """One clinical payload received from HIS/mock HIS before prediction."""

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="clinical_records")
    age = models.PositiveIntegerField()
    sex = models.TextField()
    bmi = models.FloatField()
    sp = models.FloatField()
    bp = models.FloatField()
    hba1c = models.FloatField()
    fps = models.FloatField()
    pps = models.FloatField()
    fam_ho = models.TextField()
    on_age = models.FloatField()
    dia_life = models.TextField()
    smk = models.TextField()
    phy_act = models.TextField()
    med_use = models.TextField()
    med_adh = models.TextField()
    source = models.CharField(max_length=50, default="mock_his")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.id} - {self.created_at}"


class PatientRiskStatus(models.Model):
    """Latest known complication risk status for a patient.

    This is a cache for dashboards/lists. Historical prediction details live in
    predictions.RiskScoreDetail.
    """

    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name="risk_status")
    nep = models.BooleanField(default=False, verbose_name="Nephropathy")
    neu = models.BooleanField(default=False, verbose_name="Neuropathy")
    ret = models.BooleanField(default=False, verbose_name="Retinopathy")
    cv = models.BooleanField(default=False, verbose_name="Cardiovascular complication")
    per_vas = models.BooleanField(default=False, verbose_name="Peripheral Vascular complication")
    source = models.CharField(max_length=50, default="prediction")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient.id} - {self.patient.name} - {self.pk}"
