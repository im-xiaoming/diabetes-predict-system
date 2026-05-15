from django.conf import settings
from django.db import models


class Profile(models.Model):
    class Role(models.TextChoices):
        DOCTOR = "doctor", "Bác sĩ"
        ADMIN = "admin", "Quản trị viên"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.DOCTOR,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
