from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import resolve_url

from .models import Profile


def get_role(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser or user.is_staff:
        return Profile.Role.ADMIN
    profile = getattr(user, "profile", None)
    return getattr(profile, "role", None) or Profile.Role.DOCTOR


def is_admin(user):
    return get_role(user) == Profile.Role.ADMIN


def is_doctor(user):
    return get_role(user) == Profile.Role.DOCTOR


def role_required(*roles):
    def dec(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path(), resolve_url("login"))
            if get_role(request.user) not in roles:
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapper

    return dec


doctor_or_admin_required = role_required(Profile.Role.DOCTOR, Profile.Role.ADMIN)
admin_required = role_required(Profile.Role.ADMIN)
