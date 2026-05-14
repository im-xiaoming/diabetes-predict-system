from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Profile


User = get_user_model()


class AccountsAuthTests(TestCase):
    def test_register_creates_user_and_profile(self):
        response = self.client.post(
            reverse("register"),
            {
                "full_name": "Nguyen Van A",
                "email": "doctor@example.com",
                "username": "doctor1",
                "role": Profile.Role.DOCTOR,
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
                "terms": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("login"))
        user = User.objects.get(username="doctor1")
        self.assertEqual(user.email, "doctor@example.com")
        self.assertTrue(user.check_password("StrongPass123!"))
        self.assertEqual(user.profile.role, Profile.Role.DOCTOR)

    def test_login_accepts_username(self):
        user = User.objects.create_user(
            username="doctor1",
            email="doctor@example.com",
            password="StrongPass123!",
        )

        response = self.client.post(
            reverse("login"),
            {"username": "doctor1", "password": "StrongPass123!"},
        )

        self.assertRedirects(response, reverse("login"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_login_accepts_email(self):
        user = User.objects.create_user(
            username="doctor1",
            email="doctor@example.com",
            password="StrongPass123!",
        )

        response = self.client.post(
            reverse("login"),
            {"username": "doctor@example.com", "password": "StrongPass123!"},
        )

        self.assertRedirects(response, reverse("login"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_register_success_message_is_consumed_on_login_page(self):
        response = self.client.post(
            reverse("register"),
            {
                "full_name": "Nguyen Van A",
                "email": "message@example.com",
                "username": "messageuser",
                "role": Profile.Role.PATIENT,
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
                "terms": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("login"))

        login_response = self.client.get(reverse("login"))
        self.assertContains(login_response, "Đăng ký thành công")

        admin_response = self.client.get("/admin/login/")
        self.assertNotContains(admin_response, "Đăng ký thành công")
