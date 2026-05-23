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

DEFAULT_MODEL_TRAINING_CONFIG = {
    "tune": True,
    "n_trials": 5,
    "timeout": 600,
    "register": True,
    "promotion_metric": "f1_macro",
    "promotion_min_delta": 0.01,
    "force_promote": False,
    "log_optuna_trials": False,
    "enabled_models": ["logistic_regression", "random_forest"],
    "optuna": {
        "n_splits": 3,
        "random_state": 42,
    },
    "search_space": {
        "logistic_regression": {
            "C": {"low": 0.001, "high": 10.0, "log": True},
            "penalty": ["l2"],
            "solver": ["lbfgs", "liblinear"],
            "max_iter": 2000,
            "class_weight": "balanced",
        },
        "random_forest": {
            "n_estimators": {"low": 100, "high": 600, "step": 50},
            "max_depth": {"low": 3, "high": 20},
            "min_samples_split": {"low": 2, "high": 20},
            "min_samples_leaf": {"low": 1, "high": 10},
            "max_features": ["sqrt", "log2", None],
            "class_weight": "balanced",
            "n_jobs": -1,
        },
        "xgboost": {
            "n_estimators": {"low": 100, "high": 600, "step": 50},
            "max_depth": {"low": 3, "high": 10},
            "learning_rate": {"low": 0.001, "high": 0.3, "log": True},
            "subsample": {"low": 0.6, "high": 1.0},
            "colsample_bytree": {"low": 0.6, "high": 1.0},
            "min_child_weight": {"low": 1, "high": 10},
            "gamma": {"low": 0.0, "high": 5.0},
            "reg_lambda": {"low": 0.001, "high": 10.0, "log": True},
            "eval_metric": "logloss",
        },
    },
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


def default_enabled_models():
    return list(DEFAULT_MODEL_TRAINING_CONFIG["enabled_models"])


def default_optuna_config():
    return dict(DEFAULT_MODEL_TRAINING_CONFIG["optuna"])


def default_search_space():
    return json.loads(json.dumps(DEFAULT_MODEL_TRAINING_CONFIG["search_space"]))


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


class ModelTrainingConfig(models.Model):
    tune = models.BooleanField(
        default=DEFAULT_MODEL_TRAINING_CONFIG["tune"],
        help_text="Use Optuna to tune model hyperparameters.",
    )
    n_trials = models.PositiveIntegerField(
        default=DEFAULT_MODEL_TRAINING_CONFIG["n_trials"],
        help_text="Number of Optuna trials per model family.",
    )
    timeout = models.PositiveIntegerField(
        default=DEFAULT_MODEL_TRAINING_CONFIG["timeout"],
        help_text="Optuna timeout in seconds per model family.",
    )
    register = models.BooleanField(
        default=DEFAULT_MODEL_TRAINING_CONFIG["register"],
        help_text="Register the promoted model in MLflow Model Registry.",
    )
    promotion_metric = models.CharField(
        max_length=64,
        default=DEFAULT_MODEL_TRAINING_CONFIG["promotion_metric"],
        help_text="Metric used to compare candidate model with champion.",
    )
    promotion_min_delta = models.FloatField(
        default=DEFAULT_MODEL_TRAINING_CONFIG["promotion_min_delta"],
        help_text="Minimum metric improvement required to promote a candidate.",
    )
    force_promote = models.BooleanField(
        default=DEFAULT_MODEL_TRAINING_CONFIG["force_promote"],
        help_text="Promote candidate even when it is worse than champion.",
    )
    log_optuna_trials = models.BooleanField(
        default=DEFAULT_MODEL_TRAINING_CONFIG["log_optuna_trials"],
        help_text="Log each Optuna trial to MLflow. This creates many runs.",
    )
    enabled_models = models.JSONField(
        default=default_enabled_models,
        help_text='Model families to train, e.g. ["logistic_regression", "random_forest"].',
    )
    optuna = models.JSONField(
        default=default_optuna_config,
        help_text="Optuna and cross-validation settings.",
    )
    search_space = models.JSONField(
        default=default_search_space,
        help_text="Hyperparameter search spaces per model family.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Model training config"
        verbose_name_plural = "Model training config"

    def __str__(self):
        return f"Model training config: {self.n_trials} trials"

    def clean(self):
        super().clean()
        if self.pk is None and ModelTrainingConfig.objects.exists():
            raise ValidationError("Only one model training config can exist.")

        if not isinstance(self.enabled_models, list) or not self.enabled_models:
            raise ValidationError({"enabled_models": "Must be a non-empty JSON list."})
        if not isinstance(self.optuna, dict):
            raise ValidationError({"optuna": "Must be a JSON object."})
        if not isinstance(self.search_space, dict):
            raise ValidationError({"search_space": "Must be a JSON object."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        self.write_training_config()

    def as_config(self):
        return {
            "tune": self.tune,
            "n_trials": self.n_trials,
            "timeout": self.timeout,
            "register": self.register,
            "promotion_metric": self.promotion_metric,
            "promotion_min_delta": self.promotion_min_delta,
            "force_promote": self.force_promote,
            "log_optuna_trials": self.log_optuna_trials,
            "enabled_models": self.enabled_models,
            "optuna": self.optuna,
            "search_space": self.search_space,
        }

    def write_training_config(self):
        config_path = Path(
            getattr(
                settings,
                "MODEL_TRAINING_CONFIG_PATH",
                settings.BASE_DIR / "configs" / "model_training_config.json",
            )
        )
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(self.as_config(), indent=2) + "\n",
            encoding="utf-8",
        )
