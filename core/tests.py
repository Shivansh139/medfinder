"""Automated tests for the core app. Run with: python manage.py test"""

from unittest import mock

from django.db import OperationalError
from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class HomePageTests(TestCase):
    def test_home_page_loads(self):
        """The home page returns HTTP 200 and uses the right template."""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")
        self.assertTemplateUsed(response, "base.html")

    def test_home_page_shows_brand(self):
        """The navbar brand and main heading appear on the page."""
        response = self.client.get(reverse("home"))
        self.assertContains(response, "MediFind")
        self.assertContains(response, "Find medicines at pharmacies near you")

    def test_logged_out_visitor_sees_login_outside_collapsed_menu(self):
        """Log in / Sign up must be visible on phones without opening the menu."""
        html = self.client.get(reverse("home")).content.decode()
        login_link = f'href="{reverse("login")}"'
        signup_link = f'href="{reverse("signup")}"'
        # Each link appears exactly once (in the navbar, not repeated on the page).
        self.assertEqual(html.count(login_link), 1)
        self.assertEqual(html.count(signup_link), 1)
        # The navbar Log in link comes before the collapsible menu, i.e. outside it.
        self.assertLess(html.index(login_link), html.index('id="mainNav"'))

    def test_logged_in_user_does_not_see_login_buttons(self):
        User.objects.create_user("asha", password="Str0ng-Test-Pass!")
        self.client.login(username="asha", password="Str0ng-Test-Pass!")
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, f'href="{reverse("login")}"')
        self.assertNotContains(response, f'href="{reverse("signup")}"')
        self.assertContains(response, f'href="{reverse("dashboard")}"', count=1)


class HealthCheckTests(TestCase):
    def test_health_check_says_ok(self):
        """Render calls /healthz/; it must answer 200 "ok" without logging in."""
        response = self.client.get(reverse("health_check"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")
        self.assertIn("no-cache", response["Cache-Control"])

    def test_health_check_reports_database_problem(self):
        """If the database cannot be reached, answer 503 instead of crashing."""
        with mock.patch("core.views.connection.cursor", side_effect=OperationalError):
            response = self.client.get(reverse("health_check"))
        self.assertEqual(response.status_code, 503)

    def test_health_check_rejects_post(self):
        self.assertEqual(self.client.post(reverse("health_check")).status_code, 405)


class ErrorPageTests(TestCase):
    def test_missing_page_uses_friendly_404(self):
        """Tests run with DEBUG off, like production, so our 404.html is used."""
        response = self.client.get("/no-such-page/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertContains(response, "Page not found", status_code=404)
