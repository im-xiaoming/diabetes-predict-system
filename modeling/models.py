import json
import re
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


SCHEDULE_HELP = (
    "Cron: 0 2 * * *; Airflow preset: @daily; interval: 15m, 2h, 1d; "
    "or manual/none to disable automatic scheduling."
)

DEFAULT_RETRAIN_CONFIG = {
    "schedule": "1d",
    "min_new_labels": 100,
    "min_new_ratio": 0.10,
    "min_new_positives": 20,
    "min_positive_targets": 2,
    "min_days": 7,
    "urgent_new_labels": 500,
    "max_missing_rate": 0.05,
    "max_duplicate_rate": 0.30,
    "force": False,
}


def validate_retrain_schedule(value):
    raw_value = (value or "").strip()
    lowered = raw_value.lower()
    if lowered in {"", "none", "manual", "manual_only", "off"}:
        return
    if lowered.startswith("@"):
        return
    if re.fullmatch(
        r"[1-9]\d*\s*(m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days)",
        lowered,
    ):
        return
    if len(raw_value.split()) in {5, 6, 7}:
        return
    raise ValidationError(SCHEDULE_HELP)


def validate_ratio(value):
    if value < 0 or value > 1:
        raise ValidationError("Value must be between 0 and 1.")


class AirflowRetrainConfig(models.Model):
    schedule = models.CharField(
        max_length=64,
        default=DEFAULT_RETRAIN_CONFIG["schedule"],
        validators=[validate_retrain_schedule],
        help_text=SCHEDULE_HELP,
    )
    min_new_labels = models.PositiveIntegerField(
        default=DEFAULT_RETRAIN_CONFIG["min_new_labels"],
        help_text="Minimum new labeled records required before retraining.",
    )
    min_new_ratio = models.FloatField(
        default=DEFAULT_RETRAIN_CONFIG["min_new_ratio"],
        validators=[validate_ratio],
        help_text="Minimum new-label ratio compared with current training rows.",
    )
    min_new_positives = models.PositiveIntegerField(
        default=DEFAULT_RETRAIN_CONFIG["min_new_positives"],
        help_text="Minimum new positive labels required before retraining.",
    )
    min_positive_targets = models.PositiveIntegerField(
        default=DEFAULT_RETRAIN_CONFIG["min_positive_targets"],
        help_text="Minimum number of target classes that must have positive labels.",
    )
    min_days = models.PositiveIntegerField(
        default=DEFAULT_RETRAIN_CONFIG["min_days"],
        help_text="Minimum days between successful retraining runs.",
    )
    urgent_new_labels = models.PositiveIntegerField(
        default=DEFAULT_RETRAIN_CONFIG["urgent_new_labels"],
        help_text="New-label count that can bypass the minimum-days rule.",
    )
    max_missing_rate = models.FloatField(
        default=DEFAULT_RETRAIN_CONFIG["max_missing_rate"],
        validators=[validate_ratio],
        help_text="Maximum allowed missing-value rate in new training data.",
    )
    max_duplicate_rate = models.FloatField(
        default=DEFAULT_RETRAIN_CONFIG["max_duplicate_rate"],
        validators=[validate_ratio],
        help_text="Maximum allowed duplicate-record rate in new training data.",
    )
    force = models.BooleanField(
        default=DEFAULT_RETRAIN_CONFIG["force"],
        help_text="Force retraining even when policy checks would skip it.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Airflow retrain config"
        verbose_name_plural = "Airflow retrain config"

    def __str__(self):
        return f"Retrain config: {self.schedule}"

    def clean(self):
        super().clean()
        if self.pk is None and AirflowRetrainConfig.objects.exists():
            raise ValidationError("Only one Airflow retrain config can exist.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        self.write_airflow_config()

    def as_config(self):
        return {
            "schedule": self.schedule,
            "min_new_labels": self.min_new_labels,
            "min_new_ratio": self.min_new_ratio,
            "min_new_positives": self.min_new_positives,
            "min_positive_targets": self.min_positive_targets,
            "min_days": self.min_days,
            "urgent_new_labels": self.urgent_new_labels,
            "max_missing_rate": self.max_missing_rate,
            "max_duplicate_rate": self.max_duplicate_rate,
            "force": self.force,
        }

    def write_airflow_config(self):
        config_path = Path(
            getattr(
                settings,
                "AIRFLOW_RETRAIN_CONFIG_PATH",
                settings.BASE_DIR / "configs" / "airflow_retrain_config.json",
            )
        )
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(self.as_config(), indent=2) + "\n",
            encoding="utf-8",
        )
