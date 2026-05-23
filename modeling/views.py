from django.contrib import messages
from django.db.models import Avg, Count, Max, Min
from django.http import HttpResponse
from django.shortcuts import redirect, render
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

from accounts.permissions import admin_required
from predictions.models import PredictionResult, RequestLog
from .forms import TrainModelForm


BASE_DIR = Path(__file__).resolve().parent.parent
TRAIN_SCRIPT = BASE_DIR / "ml" / "train.py"
MLFLOW_UI_URL = os.environ.get("MLFLOW_UI_URL", "http://127.0.0.1:5001")
MLFLOW_HEALTH_URL = os.environ.get("MLFLOW_HEALTH_URL", MLFLOW_UI_URL)
MLFLOW_AUTO_START = os.environ.get("MLFLOW_AUTO_START", "1").strip().lower() in {"1", "true", "yes", "on"}
REQUIRED_TRAINING_PACKAGES = ("mlflow", "optuna", "pandas", "sklearn", "joblib")
TARGET_FIELDS = {
    "NEP": "nep",
    "NEU": "neu",
    "RET": "ret",
    "CV": "cv",
    "PER VAS": "per_vas",
}


def _micro_metrics(predictions):
    tp = fp = fn = 0
    for prediction in predictions:
        label = getattr(prediction.clinical_record, "label", None)
        if not label:
            continue
        scores = {score.target: score for score in prediction.scores.all()}
        for target, field in TARGET_FIELDS.items():
            truth = bool(getattr(label, field))
            predicted = bool(getattr(scores.get(target), "risk_label", 0))
            if predicted and truth:
                tp += 1
            elif predicted and not truth:
                fp += 1
            elif not predicted and truth:
                fn += 1
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (2 * precision * recall / (precision + recall)) if precision is not None and recall is not None and precision + recall else None
    return {"precision": precision, "recall": recall, "f1": f1}


def _model_registry_rows():
    groups = (
        PredictionResult.objects.values("model_name", "model_version")
        .annotate(
            first_seen=Min("created_at"),
            last_seen=Max("created_at"),
            prediction_count=Count("id"),
        )
        .order_by("-last_seen")
    )
    latest_key = None
    rows = []
    for group in groups:
        key = (group["model_name"], group["model_version"])
        if latest_key is None:
            latest_key = key
        predictions = (
            PredictionResult.objects.filter(model_name=key[0], model_version=key[1])
            .select_related("clinical_record", "clinical_record__label")
            .prefetch_related("scores")
        )
        metrics = _micro_metrics(predictions)
        avg_latency = (
            RequestLog.objects.filter(prediction__model_name=key[0], prediction__model_version=key[1])
            .aggregate(value=Avg("latency_ms"))["value"]
            or 0
        )
        rows.append(
            {
                "model_name": key[0] or "Unknown model",
                "model_version": key[1] or "Unknown version",
                "first_seen": group["first_seen"],
                "last_seen": group["last_seen"],
                "prediction_count": group["prediction_count"],
                "avg_latency": avg_latency,
                "stage": "Production" if key == latest_key else "Archived",
                **metrics,
            }
        )
    return rows


@admin_required
def modeling(request):
    model_rows = _model_registry_rows()
    production_model = model_rows[0] if model_rows else None
    previous_model = model_rows[1] if len(model_rows) > 1 else None
    f1_delta = None
    if production_model and previous_model and production_model["f1"] is not None and previous_model["f1"] is not None:
        f1_delta = production_model["f1"] - previous_model["f1"]
    return render(
        request,
        "modeling/models.html",
        {
            "model_rows": model_rows,
            "production_model": production_model,
            "previous_model": previous_model,
            "f1_delta": f1_delta,
        },
    )


def _missing_training_packages():
    return [
        package
        for package in REQUIRED_TRAINING_PACKAGES
        if importlib.util.find_spec(package) is None
    ]


def _mlflow_ui_ready(timeout=1):
    try:
        with urlopen(MLFLOW_HEALTH_URL, timeout=timeout) as response:
            return response.status < 500
    except (OSError, URLError):
        return False


def _start_mlflow_ui():
    env = os.environ.copy()
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
    artifact_root = os.environ.get("MLFLOW_ARTIFACT_ROOT", "./mlruns")
    env["MLFLOW_TRACKING_URI"] = tracking_uri
    cmd = [
        sys.executable,
        "-m",
        "mlflow",
        "ui",
        "--backend-store-uri",
        tracking_uri,
        "--default-artifact-root",
        artifact_root,
        "--host",
        os.environ.get("MLFLOW_HOST", "127.0.0.1"),
        "--port",
        os.environ.get("MLFLOW_PORT", "5000"),
    ]
    kwargs = {
        "cwd": BASE_DIR,
        "env": env,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
        "close_fds": os.name != "nt",
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    subprocess.Popen(cmd, **kwargs)


@admin_required
def open_mlflow_ui(request):
    missing_packages = _missing_training_packages()
    if "mlflow" in missing_packages:
        return HttpResponse(
            "MLflow chua duoc cai trong Python environment dang chay Django. Hay cai bang: pip install -r requirements.txt",
            status=503,
        )

    if MLFLOW_AUTO_START and not _mlflow_ui_ready():
        try:
            _start_mlflow_ui()
        except OSError as exc:
            return HttpResponse(f"Khong the khoi dong MLflow UI: {exc}", status=503)

        for _ in range(20):
            if _mlflow_ui_ready(timeout=0.5):
                break
            time.sleep(0.5)

    return redirect(MLFLOW_UI_URL)


@admin_required
def train_model_view(request):
    if request.method == "POST":
        form = TrainModelForm(request.POST)

        if form.is_valid():
            missing_packages = _missing_training_packages()
            if missing_packages:
                messages.error(
                    request,
                    "Không thể chạy training vì thiếu package: "
                    + ", ".join(missing_packages)
                    + ". Hãy cài bằng: pip install -r requirements.txt",
                )
                return redirect("train_model")

            cmd = [
                sys.executable,
                "-u",
                str(TRAIN_SCRIPT),
            ]

            if form.cleaned_data["tune"]:
                cmd.append("--tune")

            cmd.extend(["--n-trials", str(form.cleaned_data["n_trials"])])
            cmd.extend(["--timeout", str(form.cleaned_data["timeout"])])

            if form.cleaned_data["register"]:
                cmd.append("--register")

            try:
                print("\n=== START TRAINING MODEL ===", flush=True)
                print("Command:", " ".join(cmd), flush=True)
                completed = subprocess.run(cmd, cwd=BASE_DIR)
                print("=== END TRAINING MODEL ===\n", flush=True)
            except OSError as exc:
                messages.error(request, f"Không thể khởi chạy training: {exc}")
                return redirect("train_model")

            if completed.returncode != 0:
                messages.error(
                    request,
                    f"Training thất bại với mã lỗi {completed.returncode}. Xem chi tiết trong console Django.",
                )
                return redirect("train_model")

            messages.success(request, "Training hoàn tất. Model mới đã được lưu thành công.")
            return redirect("modeling")
    else:
        form = TrainModelForm()

    return render(request, "modeling/train_model.html", {"form": form})
