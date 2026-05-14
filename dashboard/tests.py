from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class DashboardAccessTests(TestCase):
    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('dashboard')}",
        )

    def test_logged_in_user_can_access_dashboard(self):
        User.objects.create_user(
            username="doctor1",
            email="doctor@example.com",
            password="StrongPass123!",
        )
        self.client.login(username="doctor1", password="StrongPass123!")

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
