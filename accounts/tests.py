"""Tests for sign-up, login redirects and logout. Run with: python manage.py test"""

from django.test import TestCase
from django.urls import reverse

from pharmacies.models import Pharmacy

from .models import User

# A password that passes Django's password validators.
PASSWORD = "Str0ng-Test-Pass!"


class CustomerSignUpTests(TestCase):
    def test_customer_signup_creates_customer_and_logs_in(self):
        response = self.client.post(reverse("customer_signup"), {
            "username": "asha",
            "email": "asha@example.com",
            "password1": PASSWORD,
            "password2": PASSWORD,
        })
        self.assertRedirects(response, reverse("dashboard"))

        user = User.objects.get(username="asha")
        self.assertEqual(user.role, User.Role.CUSTOMER)
        # The new user is logged in: the session holds their id.
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_mismatched_passwords_are_rejected(self):
        response = self.client.post(reverse("customer_signup"), {
            "username": "asha",
            "email": "asha@example.com",
            "password1": PASSWORD,
            "password2": "something-else",
        })
        self.assertEqual(response.status_code, 200)  # form shown again with errors
        self.assertFalse(User.objects.filter(username="asha").exists())


class PharmacySignUpTests(TestCase):
    def signup_data(self, **overrides):
        data = {
            "username": "cityrx",
            "email": "city@example.com",
            "password1": PASSWORD,
            "password2": PASSWORD,
            "pharmacy_name": "City Pharmacy",
            "licence_number": "LIC-001",
            "address": "12 MG Road",
            "phone": "9876543210",
        }
        data.update(overrides)
        return data

    def test_pharmacy_signup_creates_pending_pharmacy(self):
        response = self.client.post(reverse("pharmacy_signup"), self.signup_data())
        self.assertRedirects(response, reverse("dashboard"), target_status_code=302)

        user = User.objects.get(username="cityrx")
        self.assertEqual(user.role, User.Role.PHARMACY)
        pharmacy = Pharmacy.objects.get(owner=user)
        self.assertEqual(pharmacy.name, "City Pharmacy")
        self.assertEqual(pharmacy.status, Pharmacy.Status.PENDING)

    def test_duplicate_licence_number_is_rejected(self):
        self.client.post(reverse("pharmacy_signup"), self.signup_data())
        self.client.logout()
        response = self.client.post(
            reverse("pharmacy_signup"),
            self.signup_data(username="other", licence_number="lic-001"),  # same, different case
        )
        self.assertContains(response, "already registered")
        self.assertFalse(User.objects.filter(username="other").exists())


class DashboardRedirectTests(TestCase):
    def test_logged_out_visitor_is_sent_to_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")

    def test_customer_sees_customer_dashboard(self):
        User.objects.create_user("asha", password=PASSWORD, role=User.Role.CUSTOMER)
        self.client.login(username="asha", password=PASSWORD)
        response = self.client.get(reverse("dashboard"))
        self.assertTemplateUsed(response, "accounts/customer_dashboard.html")

    def test_pharmacy_goes_to_pharmacy_dashboard(self):
        User.objects.create_user("cityrx", password=PASSWORD, role=User.Role.PHARMACY)
        self.client.login(username="cityrx", password=PASSWORD)
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, reverse("pharmacy_dashboard"))

    def test_admin_goes_to_admin_site(self):
        User.objects.create_superuser("boss", password=PASSWORD)
        self.client.login(username="boss", password=PASSWORD)
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, reverse("admin:index"))

    def test_login_page_redirects_to_dashboard(self):
        User.objects.create_user("asha", password=PASSWORD)
        response = self.client.post(reverse("login"), {"username": "asha", "password": PASSWORD})
        self.assertRedirects(response, reverse("dashboard"))


class UserModelTests(TestCase):
    def test_superuser_always_has_admin_role(self):
        user = User.objects.create_superuser("boss", password=PASSWORD)
        self.assertEqual(user.role, User.Role.ADMIN)


class LogoutTests(TestCase):
    def test_logout_with_post_logs_user_out(self):
        User.objects.create_user("asha", password=PASSWORD)
        self.client.login(username="asha", password=PASSWORD)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)
