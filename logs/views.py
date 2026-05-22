from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from predictions.models import RequestLog


@login_required(login_url="login")
def logs(request):
    log_list = (
        RequestLog.objects.select_related("prediction", "prediction__patient")
        .order_by("-created_at")
    )
    paginator = Paginator(log_list, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    latest_log = log_list.first()
    return render(
        request,
        "logs/logs.html",
        {
            "logs": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "latest_log": latest_log,
        },
    )
