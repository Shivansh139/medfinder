"""Tests for pharmacy permissions and admin approval. Run with: python manage.py test"""

from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Pharmacy

PASSWORD = "Str0ng-Test-Pass!"


def make_pharmacy(username="cityrx", licence="LIC-001"):
    """Create a pharmacy user plus their (pending) pharmacy."""
    user = User.objects.create_user(username, password=PASSWORD, role=User.Role.PHARMACY)
    pharmacy = Pharmacy.objects.create(
        owner=user, name="City Pharmacy", licence_number=licence,
        address="12 MG Road", phone="9876543210",
    )
    return user, pharmacy


class PharmacyDashboardPermissionTests(TestCase):
    url = reverse("pharmacy_dashboard")

    def test_logged_out_visitor_is_sent_to_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")

    def test_customer_gets_403(self):
        User.objects.create_user("asha", password=PASSWORD, role=User.Role.CUSTOMER)
        self.client.login(username="asha", password=PASSWORD)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "403.html")

    def test_pending_pharmacy_sees_awaiting_approval(self):
        make_pharmacy()
        self.client.login(username="cityrx", password=PASSWORD)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "awaiting approval")

    def test_pharmacy_sees_only_its_own_pharmacy(self):
        make_pharmacy("cityrx", "LIC-001")
        other_user, other = make_pharmacy("townrx", "LIC-002")
        other.name = "Town Pharmacy"
        other.save()
        self.client.login(username="cityrx", password=PASSWORD)
        response = self.client.get(self.url)
        self.assertContains(response, "City Pharmacy")
        self.assertNotContains(response, "Town Pharmacy")


class AdminApprovalTests(TestCase):
    def setUp(self):
        User.objects.create_superuser("boss", password=PASSWORD)
        self.client.login(username="boss", password=PASSWORD)
        _, self.pharmacy = make_pharmacy()
        self.changelist = reverse("admin:pharmacies_pharmacy_changelist")

    def run_action(self, action):
        """Submit the admin "Action" dropdown for our one pharmacy."""
        return self.client.post(self.changelist, {
            "action": action,
            "_selected_action": [self.pharmacy.pk],
        })

    def test_approve_action(self):
        self.run_action("approve_selected")
        self.pharmacy.refresh_from_db()
        self.assertEqual(self.pharmacy.status, Pharmacy.Status.APPROVED)

    def test_reject_action(self):
        self.run_action("reject_selected")
        self.pharmacy.refresh_from_db()
        self.assertEqual(self.pharmacy.status, Pharmacy.Status.REJECTED)

    def test_non_staff_cannot_use_admin(self):
        self.client.logout()
        User.objects.create_user("asha", password=PASSWORD)
        self.client.login(username="asha", password=PASSWORD)
        self.client.post(self.changelist, {
            "action": "approve_selected",
            "_selected_action": [self.pharmacy.pk],
        })
        self.pharmacy.refresh_from_db()
        self.assertEqual(self.pharmacy.status, Pharmacy.Status.PENDING)  # unchanged


class ProfileEditTests(TestCase):
    """Phase 3: pharmacies edit their own profile and location."""

    url = reverse("pharmacy_profile")

    def setUp(self):
        self.user, self.pharmacy = make_pharmacy()
        # Start as approved, to check that editing keeps the approval.
        self.pharmacy.status = Pharmacy.Status.APPROVED
        self.pharmacy.save()

    def valid_data(self, **overrides):
        data = {
            "name": "City Pharmacy Plus",
            "address": "14 MG Road",
            "phone": "9123456780",
            "opening_hours": "9 am – 9 pm, closed Sunday",
            "latitude": "12.971599",
            "longitude": "77.594566",
        }
        data.update(overrides)
        return data

    def login_pharmacy(self):
        self.client.login(username="cityrx", password=PASSWORD)

    # --- Permissions ---

    def test_logged_out_visitor_is_sent_to_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")

    def test_customer_gets_403(self):
        User.objects.create_user("asha", password=PASSWORD, role=User.Role.CUSTOMER)
        self.client.login(username="asha", password=PASSWORD)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, self.valid_data()).status_code, 403)

    # --- Successful edit ---

    def test_pharmacy_updates_own_profile_and_location(self):
        self.login_pharmacy()
        response = self.client.post(self.url, self.valid_data())
        self.assertRedirects(response, reverse("pharmacy_dashboard"))

        self.pharmacy.refresh_from_db()
        self.assertEqual(self.pharmacy.name, "City Pharmacy Plus")
        self.assertEqual(self.pharmacy.opening_hours, "9 am – 9 pm, closed Sunday")
        self.assertEqual(str(self.pharmacy.latitude), "12.971599")
        self.assertEqual(str(self.pharmacy.longitude), "77.594566")
        # Decision 1: an approved pharmacy stays approved after editing.
        self.assertEqual(self.pharmacy.status, Pharmacy.Status.APPROVED)

    def test_location_and_opening_hours_are_optional(self):
        self.login_pharmacy()
        response = self.client.post(
            self.url, self.valid_data(latitude="", longitude="", opening_hours="")
        )
        self.assertRedirects(response, reverse("pharmacy_dashboard"))
        self.pharmacy.refresh_from_db()
        self.assertFalse(self.pharmacy.has_location)

    # --- Server-side validation ---

    def test_latitude_out_of_range_is_rejected(self):
        self.login_pharmacy()
        response = self.client.post(self.url, self.valid_data(latitude="95"))
        self.assertEqual(response.status_code, 200)  # form shown again
        self.assertContains(response, "less than or equal to 90")
        self.pharmacy.refresh_from_db()
        self.assertIsNone(self.pharmacy.latitude)

    def test_longitude_out_of_range_is_rejected(self):
        self.login_pharmacy()
        response = self.client.post(self.url, self.valid_data(longitude="-181"))
        self.assertContains(response, "greater than or equal to -180")

    def test_latitude_without_longitude_is_rejected(self):
        self.login_pharmacy()
        response = self.client.post(self.url, self.valid_data(longitude=""))
        self.assertContains(response, "Set both latitude and longitude")
        self.pharmacy.refresh_from_db()
        self.assertIsNone(self.pharmacy.latitude)

    def test_opening_hours_longer_than_100_characters_is_rejected(self):
        self.login_pharmacy()
        response = self.client.post(self.url, self.valid_data(opening_hours="x" * 101))
        self.assertContains(response, "at most 100 characters")

    def test_tampered_status_and_licence_are_ignored(self):
        """Extra fields added to the request by hand must not change locked data."""
        self.pharmacy.status = Pharmacy.Status.PENDING
        self.pharmacy.save()
        self.login_pharmacy()
        self.client.post(
            self.url, self.valid_data(status="approved", licence_number="HACKED-999")
        )
        self.pharmacy.refresh_from_db()
        self.assertEqual(self.pharmacy.status, Pharmacy.Status.PENDING)
        self.assertEqual(self.pharmacy.licence_number, "LIC-001")
        self.assertEqual(self.pharmacy.name, "City Pharmacy Plus")  # allowed fields did save


class DashboardLocationTests(TestCase):
    def setUp(self):
        _, self.pharmacy = make_pharmacy()
        self.client.login(username="cityrx", password=PASSWORD)

    def test_warning_shown_when_location_missing(self):
        response = self.client.get(reverse("pharmacy_dashboard"))
        self.assertContains(response, "Set your location so customers can find you")
        self.assertNotContains(response, 'id="location-map"')

    def test_map_and_opening_hours_shown_when_set(self):
        self.pharmacy.latitude = "12.971599"
        self.pharmacy.longitude = "77.594566"
        self.pharmacy.opening_hours = "8 am – 10 pm"
        self.pharmacy.save()
        response = self.client.get(reverse("pharmacy_dashboard"))
        self.assertNotContains(response, "Set your location so customers can find you")
        self.assertContains(response, 'data-lat="12.971599"')
        self.assertContains(response, "8 am – 10 pm")


class HomeDeliveryTests(TestCase):
    """Phase 4: home delivery needs a phone number."""

    url = reverse("pharmacy_profile")

    def setUp(self):
        make_pharmacy()
        self.client.login(username="cityrx", password=PASSWORD)

    def profile_data(self, **overrides):
        data = {"name": "City Pharmacy", "address": "12 MG Road", "phone": "9876543210",
                "opening_hours": "", "latitude": "", "longitude": ""}
        data.update(overrides)
        return data

    def test_delivery_without_phone_is_rejected(self):
        response = self.client.post(self.url, self.profile_data(home_delivery_available="on"))
        self.assertContains(response, "Enter a delivery phone number")
        self.assertFalse(Pharmacy.objects.get().home_delivery_available)

    def test_delivery_with_phone_is_saved_and_shown(self):
        response = self.client.post(self.url, self.profile_data(
            home_delivery_available="on", home_delivery_phone="9000011111"))
        self.assertRedirects(response, reverse("pharmacy_dashboard"))
        pharmacy = Pharmacy.objects.get()
        self.assertTrue(pharmacy.home_delivery_available)
        self.assertContains(self.client.get(reverse("pharmacy_dashboard")), "Yes · 9000011111")

    def test_unticking_delivery_clears_old_phone(self):
        self.client.post(self.url, self.profile_data(
            home_delivery_available="on", home_delivery_phone="9000011111"))
        # A checkbox that is not ticked is simply missing from the POST data.
        self.client.post(self.url, self.profile_data(home_delivery_phone="9000011111"))
        pharmacy = Pharmacy.objects.get()
        self.assertFalse(pharmacy.home_delivery_available)
        self.assertEqual(pharmacy.home_delivery_phone, "")


class AdminAddPharmacyDisabledTests(TestCase):
    def test_admin_cannot_add_pharmacy(self):
        User.objects.create_superuser("boss", password=PASSWORD)
        self.client.login(username="boss", password=PASSWORD)
        response = self.client.get(reverse("admin:pharmacies_pharmacy_add"))
        self.assertEqual(response.status_code, 403)
        changelist = self.client.get(reverse("admin:pharmacies_pharmacy_changelist"))
        self.assertNotContains(changelist, reverse("admin:pharmacies_pharmacy_add"))
