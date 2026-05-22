from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from predictions.models import PredictionResult

# Create your views here.
@login_required(login_url="login")
def history(request):
    prediction_list = (
        PredictionResult.objects.select_related("patient")
        .prefetch_related("scores")
        .order_by("-created_at")
    )
    paginator = Paginator(prediction_list, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    rows = []
    for prediction in page_obj.object_list:
        scores = {score.target: score for score in prediction.scores.all()}
        rows.append(
            {
                "prediction": prediction,
                "nep": scores.get("NEP"),
                "neu": scores.get("NEU"),
                "ret": scores.get("RET"),
                "cv": scores.get("CV"),
                "per_vas": scores.get("PER VAS"),
            }
        )

    return render(
        request,
        "history/prediction_history.html",
        {
            "rows": rows,
            "page_obj": page_obj,
            "paginator": paginator,
        },
    )


@login_required(login_url="login")
def history_detail(request):
    return render(request, "history/prediction_detail.html")
