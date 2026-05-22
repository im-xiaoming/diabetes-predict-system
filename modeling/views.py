from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
import importlib.util
from pathlib import Path
import subprocess
import sys

from .forms import TrainModelForm


BASE_DIR = Path(__file__).resolve().parent.parent
TRAIN_SCRIPT = BASE_DIR / "ml" / "train.py"
REQUIRED_TRAINING_PACKAGES = ("mlflow", "optuna", "pandas", "sklearn", "joblib")


@login_required(login_url="login")
def modeling(request):
    return render(request, "modeling/models.html")


def _missing_training_packages():
    return [
        package
        for package in REQUIRED_TRAINING_PACKAGES
        if importlib.util.find_spec(package) is None
    ]


@login_required(login_url="login")
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
