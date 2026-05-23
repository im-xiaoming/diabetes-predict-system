from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile


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

    def test_doctor_sidebar_hides_admin_tools(self):
        user = User.objects.create_user(
            username="doctor2",
            email="doctor2@example.com",
            password="StrongPass123!",
        )
        Profile.objects.create(user=user, role=Profile.Role.DOCTOR)
        self.client.login(username="doctor2", password="StrongPass123!")

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard")
        self.assertContains(response, "Patients")
        self.assertContains(response, "Alerts")
        self.assertContains(response, "History")
        self.assertNotContains(response, "MLflow")
        self.assertNotContains(response, "Airflow")
        self.assertNotContains(response, "Grafana")
        self.assertNotContains(response, "Mock HIS")
        self.assertNotContains(response, "System Monitoring")
        self.assertNotContains(response, "Logging")

    def test_admin_sidebar_shows_admin_tools(self):
        user = User.objects.create_user(
            username="admin1",
            email="admin@example.com",
            password="StrongPass123!",
        )
        Profile.objects.create(user=user, role=Profile.Role.ADMIN)
        self.client.login(username="admin1", password="StrongPass123!")

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Model")
        self.assertContains(response, "External MLOps Tools")
        self.assertContains(response, "MLflow")
        self.assertContains(response, "Airflow")
        self.assertContains(response, "Grafana")
        self.assertContains(response, "Mock HIS")
        self.assertContains(response, "System Monitoring")
        self.assertContains(response, "Logging")

    def test_doctor_cannot_access_admin_pages(self):
        user = User.objects.create_user(
            username="doctor3",
            email="doctor3@example.com",
            password="StrongPass123!",
        )
        Profile.objects.create(user=user, role=Profile.Role.DOCTOR)
        self.client.login(username="doctor3", password="StrongPass123!")

        for name in ["modeling", "monitor", "logging", "mock-his", "his-inference"]:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 403, name)

    def test_admin_can_access_admin_pages(self):
        user = User.objects.create_user(
            username="admin2",
            email="admin2@example.com",
            password="StrongPass123!",
        )
        Profile.objects.create(user=user, role=Profile.Role.ADMIN)
        self.client.login(username="admin2", password="StrongPass123!")

        for name in ["modeling", "monitor", "logging", "mock-his", "his-inference"]:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)
