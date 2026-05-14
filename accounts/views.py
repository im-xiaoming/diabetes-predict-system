from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect, render

from .forms import LoginForm, RegisterForm


def login_view(request):
    form = LoginForm(request, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        auth_login(request, form.get_user())
        return redirect('dashboard')

    return render(request, "accounts/login.html", {"form": form})


def register(request):
    form = RegisterForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Đăng ký thành công. Bạn có thể đăng nhập.")
            return redirect("login")

    return render(request, "accounts/register.html", {"form": form})


def logout_view(request):
    auth_logout(request)
    messages.success(request, "Đã đăng xuất.")
    return redirect("login")


def forgot_password(request):
    return render(request, "accounts/forgot_password.html")
