from django.shortcuts import render

# Create your views here.
def alerts(request):
    return render(request, "alerts/alerts.html")