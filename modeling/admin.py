import os
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.db.models import Avg, Count, Max, Min
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from predictions.models import PredictionResult, RequestLog, RiskScoreDetail
from .models import AirflowRetrainConfig, ModelTrainingConfig


def model_artifact_info():
    path = settings.BASE_DIR / "ml" / "artifacts" / "model.pkl"
    if not path.exists():
        return {"exists": False, "path": str(path), "size_mb": None, "modified_at": None}
    stat = path.stat()
    return {
        "exists": True,
        "path": str(path),
        "size_mb": round(stat.st_size / (1024 * 1024), 3),
        "modified_at": timezone.datetime.fromtimestamp(stat.st_mtime, tz=timezone.get_current_timezone()),
    }


def prepare_mlflow_tracking_uri():
    uri = os.environ.get("MLFLOW_TRACKING_URI")
    local_db = settings.BASE_DIR / "mlflow.db"
    if not uri:
        os.environ["MLFLOW_TRACKING_URI"] = f"sqlite:///{local_db.as_posix()}"
        return None
    elif not uri.startswith("sqlite:///"):
        return None
    else:
        raw_path = uri.removeprefix("sqlite:///")
        if raw_path == ":memory:":
            return None
        path = Path(raw_path)
        if raw_path.startswith("/app/") and local_db.exists():
            os.environ["MLFLOW_TRACKING_URI"] = f"sqlite:///{local_db.as_posix()}"
            return None
        if not path.is_absolute():
            path = settings.BASE_DIR / path

    if not path.parent.exists() and local_db.exists():
        os.environ["MLFLOW_TRACKING_URI"] = f"sqlite:///{local_db.as_posix()}"
        return None
    if not path.parent.exists():
        return "Chưa kết nối được MLflow. Nếu chạy local, hãy dùng MLFLOW_TRACKING_URI=sqlite:///mlflow.db hoặc khởi động MLflow UI."
    return None


def champion_model_info():
    storage_error = prepare_mlflow_tracking_uri()
    if storage_error:
        return {"available": False, "error": storage_error}

    try:
        from ml.registry import get_champion_metrics
        from ml.tracking import setup_tracking
        from mlflow.tracking import MlflowClient
    except Exception as exc:
        return {"available": False, "error": f"Không đọc được MLflow registry: {exc}"}

    try:
        info = get_champion_metrics()
    except Exception as exc:
        return {"available": False, "error": f"Không lấy được champion model: {exc}"}

    if not info:
        return {"available": False, "error": "Chưa có champion model trong MLflow registry"}

    try:
        setup_tracking()
        run = MlflowClient().get_run(info["run_id"])
        info["params"] = dict(run.data.params)
        info["run_metrics"] = dict(run.data.metrics)
    except Exception as exc:
        info["params"] = {}
        info["run_metrics"] = {}
        info["run_error"] = f"Không đọc được params/metrics của run: {exc}"

    info["available"] = True
    return info


def fmt_metric(value):
    return "-" if value is None else f"{value:.4f}"


def dict_lines(value):
    if not value:
        return "-"
    return "<br>".join(f"{key}: {val}" for key, val in value.items())


def model_version_rows():
    groups = list(
        PredictionResult.objects.values("model_name", "model_version")
        .annotate(
            first_seen=Min("created_at"),
            last_seen=Max("created_at"),
            prediction_count=Count("id"),
        )
        .order_by("-last_seen")[:10]
    )
    rows = []
    latest_key = None
    for group in groups:
        key = (group["model_name"], group["model_version"])
        if latest_key is None:
            latest_key = key
        avg_latency = (
            RequestLog.objects.filter(prediction__model_name=key[0], prediction__model_version=key[1])
            .aggregate(value=Avg("latency_ms"))["value"]
            or 0
        )
        risk_counts = {
            item["risk_level"]: item["total"]
            for item in RiskScoreDetail.objects.filter(
                prediction__model_name=key[0],
                prediction__model_version=key[1],
            )
            .values("risk_level")
            .annotate(total=Count("id"))
        }
        positive_targets = {
            item["target"]: item["total"]
            for item in RiskScoreDetail.objects.filter(
                prediction__model_name=key[0],
                prediction__model_version=key[1],
                risk_label=1,
            )
            .values("target")
            .annotate(total=Count("id"))
        }
        rows.append(
            {
                "model_name": key[0] or "Unknown model",
                "model_version": key[1] or "Unknown version",
                "stage": "Đang dùng gần nhất" if key == latest_key else "Đã lưu lịch sử",
                "first_seen": group["first_seen"],
                "last_seen": group["last_seen"],
                "prediction_count": group["prediction_count"],
                "avg_latency": avg_latency,
                "risk_counts": risk_counts,
                "positive_targets": positive_targets,
            }
        )
    return rows


@admin.register(AirflowRetrainConfig)
class AirflowRetrainConfigAdmin(admin.ModelAdmin):
    list_display = ("schedule", "min_new_labels", "min_new_ratio", "force", "updated_at")
    readonly_fields = ("updated_at",)
    fieldsets = (
        ("Schedule", {"fields": ("schedule",)}),
        (
            "Policy thresholds",
            {
                "fields": (
                    "min_new_labels",
                    "min_new_ratio",
                    "min_new_positives",
                    "min_positive_targets",
                    "min_days",
                    "urgent_new_labels",
                    "max_missing_rate",
                    "max_duplicate_rate",
                )
            },
        ),
        ("Manual override", {"fields": ("force",)}),
        ("Audit", {"fields": ("updated_at",)}),
    )

    def has_add_permission(self, request):
        return not AirflowRetrainConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ModelTrainingConfig)
class ModelTrainingConfigAdmin(admin.ModelAdmin):
    list_display = (
        "n_trials",
        "timeout",
        "tune",
        "register",
        "promotion_metric",
        "promotion_min_delta",
        "model_artifact_status",
        "updated_at",
    )
    readonly_fields = (
        "model_artifact_summary",
        "champion_model_summary",
        "model_versions_summary",
        "updated_at",
    )
    fieldsets = (
        (
            "Model registry",
            {"fields": ("model_artifact_summary", "champion_model_summary", "model_versions_summary")},
        ),
        (
            "Training",
            {
                "fields": (
                    "tune",
                    "enabled_models",
                    "n_trials",
                    "timeout",
                    "log_optuna_trials",
                )
            },
        ),
        (
            "Promotion",
            {
                "fields": (
                    "register",
                    "promotion_metric",
                    "promotion_min_delta",
                    "force_promote",
                )
            },
        ),
        ("Optuna", {"fields": ("optuna", "search_space")}),
        ("Audit", {"fields": ("updated_at",)}),
    )

    def has_add_permission(self, request):
        return not ModelTrainingConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def model_artifact_status(self, obj=None):
        artifact = model_artifact_info()
        return "Đã có model.pkl" if artifact["exists"] else "Chưa có model.pkl"

    model_artifact_status.short_description = "Artifact"

    def model_artifact_summary(self, obj=None):
        artifact = model_artifact_info()
        status = "Đã có model.pkl" if artifact["exists"] else "Chưa có model.pkl"
        modified_at = artifact["modified_at"].strftime("%H:%M, %d/%m/%Y") if artifact["modified_at"] else "-"
        size = f'{artifact["size_mb"]} MB' if artifact["size_mb"] is not None else "-"
        return format_html(
            "<strong>{}</strong><br>Đường dẫn: <code>{}</code><br>Kích thước: {}<br>Cập nhật: {}",
            status,
            artifact["path"],
            size,
            modified_at,
        )

    model_artifact_summary.short_description = "Model artifact FastAPI đang dùng"

    def champion_model_summary(self, obj=None):
        champion = champion_model_info()
        if not champion.get("available"):
            return format_html("<strong>Chưa kết nối được MLflow</strong><br>{}", champion.get("error", "-"))

        metrics = champion.get("metrics") or champion.get("run_metrics") or {}
        params = champion.get("params") or {}
        metric_html = "<br>".join(f"{key}: {fmt_metric(value)}" for key, value in metrics.items()) or "-"
        important_params = {
            key: params[key]
            for key in ("model_name", "targets", "features", "promotion_metric", "promotion_min_delta")
            if key in params
        }
        params_html = "<br>".join(f"{key}: {value}" for key, value in important_params.items()) or "-"
        return format_html(
            "<strong>{}</strong><br>Version: {}<br>Run ID: <code>{}</code><br><br>"
            "<strong>Metrics</strong><br>{}<br><br><strong>Tham số chính</strong><br>{}",
            champion.get("name", "-"),
            champion.get("version", "-"),
            champion.get("run_id", "-"),
            mark_safe(metric_html),
            mark_safe(params_html),
        )

    champion_model_summary.short_description = "Champion model trong MLflow"

    def model_versions_summary(self, obj=None):
        rows = model_version_rows()
        if not rows:
            return "Chưa có PredictionResult trong database."

        body = []
        for row in rows[:10]:
            body.append(
                "<tr>"
                f"<td>{row['model_name']}</td>"
                f"<td>{row['model_version']}</td>"
                f"<td>{row['stage']}</td>"
                f"<td>{row['prediction_count']}</td>"
                f"<td>{row['avg_latency']:.2f} ms</td>"
                f"<td>{dict_lines(row['risk_counts'])}</td>"
                f"<td>{dict_lines(row['positive_targets'])}</td>"
                "</tr>"
            )
        return format_html(
            '<table style="width:100%">'
            "<thead><tr>"
            "<th>Model</th><th>Version</th><th>Trạng thái</th><th>Prediction</th>"
            "<th>Latency trung bình</th><th>Risk</th><th>Target dương</th>"
            "</tr></thead><tbody>{}</tbody></table>"
            "<p>Hiển thị tối đa 10 version gần nhất từ PredictionResult. "
            "Metric train chính nằm ở phần champion MLflow bên trên.</p>",
            mark_safe("".join(body)),
        )

    model_versions_summary.short_description = "Version và metrics từ database prediction"
