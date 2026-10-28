"""Tests for availability requests (Phase 6). Run with: python manage.py test"""

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from medicines.models import InventoryItem, Medicine
from pharmacies.models import Pharmacy

from .models import AvailabilityRequest

PASSWORD = "Str0ng-Test-Pass!"
Status = AvailabilityRequest.Status


class RequestTestBase(TestCase):
    """Two customers, two pharmacies, one medicine each pharmacy lists."""

    def setUp(self):
        self.asha = User.objects.create_user("asha", password=PASSWORD, role=User.Role.CUSTOMER)
        self.ravi = User.objects.create_user("ravi", password=PASSWORD, role=User.Role.CUSTOMER)
        self.city = self.make_pharmacy("cityrx", "City Pharmacy", "LIC-1")
        self.town = self.make_pharmacy("townrx", "Town Pharmacy", "LIC-2")
        self.dolo = Medicine.objects.create(
            name="Dolo 650", brand="Micro Labs", active_ingredient="Paracetamol",
            strength="650 mg", form=Medicine.Form.TABLET, category=Medicine.Category.PAIN_FEVER,
        )
        self.city_item = InventoryItem.objects.create(pharmacy=self.city, medicine=self.dolo, quantity=0, price=30)
        self.town_item = InventoryItem.objects.create(pharmacy=self.town, medicine=self.dolo, quantity=5, price=32)

    def make_pharmacy(self, username, name, licence, status=Pharmacy.Status.APPROVED):
        user = User.objects.create_user(username, password=PASSWORD, role=User.Role.PHARMACY)
        return Pharmacy.objects.create(
            owner=user, name=name, licence_number=licence, address="Indore",
            phone="9000000000", status=status,
        )

    def make_request(self, customer, pharmacy, status=Status.PENDING, **extra):
        return AvailabilityRequest.objects.create(
            customer=customer, pharmacy=pharmacy, medicine=self.dolo, status=status, **extra
        )

    def login(self, username):
        self.client.login(username=username, password=PASSWORD)


class CreateRequestTests(RequestTestBase):
    def url(self, item=None):
        return reverse("request_create", args=[(item or self.city_item).pk])

    def test_customer_creates_request(self):
        self.login("asha")
        response = self.client.post(self.url(), {"quantity": 2, "note": "By evening", "contact_phone": "9000011111"})
        self.assertRedirects(response, reverse("my_requests"))
        r = AvailabilityRequest.objects.get()
        self.assertEqual((r.customer, r.pharmacy, r.medicine), (self.asha, self.city, self.dolo))
        self.assertEqual(r.status, Status.PENDING)
        self.assertEqual(r.quantity, 2)

    def test_out_of_stock_item_can_still_be_requested(self):
        self.assertEqual(self.city_item.quantity, 0)
        self.login("asha")
        self.client.post(self.url(), {"quantity": 1})
        self.assertEqual(AvailabilityRequest.objects.count(), 1)

    def test_logged_out_visitor_is_sent_to_login_and_back(self):
        url = self.url()
        self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}")

    def test_pharmacy_and_admin_cannot_create_requests(self):
        User.objects.create_superuser("boss", password=PASSWORD)
        for username in ["cityrx", "boss"]:
            with self.subTest(username=username):
                self.login(username)
                self.assertEqual(self.client.get(self.url()).status_code, 403)
                self.assertEqual(self.client.post(self.url(), {"quantity": 1}).status_code, 403)
        self.assertFalse(AvailabilityRequest.objects.exists())

    def test_cannot_request_from_pending_or_rejected_pharmacy(self):
        self.login("asha")
        for status in [Pharmacy.Status.PENDING, Pharmacy.Status.REJECTED]:
            with self.subTest(status=status):
                self.city.status = status
                self.city.save()
                self.assertEqual(self.client.get(self.url()).status_code, 404)

    def test_tampered_pharmacy_customer_and_status_are_ignored(self):
        self.login("asha")
        self.client.post(self.url(), {
            "quantity": 1, "pharmacy": self.town.pk, "customer": self.ravi.pk, "status": "confirmed",
        })
        r = AvailabilityRequest.objects.get()
        self.assertEqual((r.customer, r.pharmacy, r.status), (self.asha, self.city, Status.PENDING))

    def test_quantity_must_be_between_1_and_100(self):
        self.login("asha")
        for bad in [0, 101, -3]:
            with self.subTest(quantity=bad):
                response = self.client.post(self.url(), {"quantity": bad})
                self.assertEqual(response.status_code, 200)  # form shown again
                self.assertIn("quantity", response.context["form"].errors)
        self.assertFalse(AvailabilityRequest.objects.exists())

    def test_duplicate_pending_request_is_blocked(self):
        self.make_request(self.asha, self.city)
        self.login("asha")
        response = self.client.post(self.url(), {"quantity": 1})
        self.assertRedirects(response, reverse("my_requests"))
        self.assertEqual(AvailabilityRequest.objects.count(), 1)

    def test_new_request_allowed_after_old_one_is_answered(self):
        self.make_request(self.asha, self.city, status=Status.UNAVAILABLE)
        self.login("asha")
        self.client.post(self.url(), {"quantity": 1})
        self.assertEqual(AvailabilityRequest.objects.filter(status=Status.PENDING).count(), 1)

    def test_database_blocks_two_pending_requests(self):
        self.make_request(self.asha, self.city)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_request(self.asha, self.city)


class CustomerOwnershipTests(RequestTestBase):
    def test_my_requests_shows_only_own(self):
        self.make_request(self.asha, self.city, note="asha's note")
        self.make_request(self.ravi, self.town, note="ravi's note")
        self.login("asha")
        response = self.client.get(reverse("my_requests"))
        self.assertContains(response, "asha&#x27;s note")
        self.assertNotContains(response, "ravi&#x27;s note")

    def test_customer_cannot_cancel_someone_elses_request(self):
        ravis = self.make_request(self.ravi, self.town)
        self.login("asha")
        response = self.client.post(reverse("request_cancel", args=[ravis.pk]))
        self.assertEqual(response.status_code, 404)
        ravis.refresh_from_db()
        self.assertEqual(ravis.status, Status.PENDING)

    def test_customer_cancels_own_pending_request(self):
        mine = self.make_request(self.asha, self.city)
        self.login("asha")
        self.client.post(reverse("request_cancel", args=[mine.pk]))
        mine.refresh_from_db()
        self.assertEqual(mine.status, Status.CANCELLED)

    def test_cancel_needs_post(self):
        mine = self.make_request(self.asha, self.city)
        self.login("asha")
        self.assertEqual(self.client.get(reverse("request_cancel", args=[mine.pk])).status_code, 405)
        mine.refresh_from_db()
        self.assertEqual(mine.status, Status.PENDING)

    def test_answered_request_cannot_be_cancelled(self):
        mine = self.make_request(self.asha, self.city, status=Status.CONFIRMED)
        self.login("asha")
        self.client.post(reverse("request_cancel", args=[mine.pk]))
        mine.refresh_from_db()
        self.assertEqual(mine.status, Status.CONFIRMED)

    def test_pharmacy_cannot_open_customer_pages(self):
        self.login("cityrx")
        self.assertEqual(self.client.get(reverse("my_requests")).status_code, 403)


class PharmacyOwnershipTests(RequestTestBase):
    def respond_url(self, r):
        return reverse("request_respond", args=[r.pk])

    def test_pharmacy_sees_only_its_own_requests(self):
        self.make_request(self.asha, self.city, note="for city")
        self.make_request(self.ravi, self.town, note="for town")
        self.login("cityrx")
        response = self.client.get(reverse("pharmacy_requests"))
        self.assertContains(response, "for city")
        self.assertNotContains(response, "for town")
        self.assertEqual(response.context["pending_count"], 1)

    def test_pending_tab_hides_answered_and_all_tab_shows_them(self):
        self.make_request(self.asha, self.city, note="still pending")
        self.make_request(self.ravi, self.city, status=Status.CONFIRMED, note="already answered")
        self.login("cityrx")
        pending = self.client.get(reverse("pharmacy_requests"))
        self.assertContains(pending, "still pending")
        self.assertNotContains(pending, "already answered")
        everything = self.client.get(reverse("pharmacy_requests"), {"show": "all"})
        self.assertContains(everything, "already answered")

    def test_pharmacy_confirms_own_request(self):
        r = self.make_request(self.asha, self.city)
        self.login("cityrx")
        response = self.client.post(self.respond_url(r), {"status": "confirmed", "pharmacy_reply": "Come by 9 pm"})
        self.assertRedirects(response, reverse("pharmacy_requests"))
        r.refresh_from_db()
        self.assertEqual(r.status, Status.CONFIRMED)
        self.assertEqual(r.pharmacy_reply, "Come by 9 pm")
        self.assertIsNotNone(r.responded_at)

    def test_pharmacy_marks_unavailable(self):
        r = self.make_request(self.asha, self.city)
        self.login("cityrx")
        self.client.post(self.respond_url(r), {"status": "unavailable"})
        r.refresh_from_db()
        self.assertEqual(r.status, Status.UNAVAILABLE)

    def test_pharmacy_cannot_respond_to_another_pharmacys_request(self):
        r = self.make_request(self.asha, self.town)
        self.login("cityrx")
        self.assertEqual(self.client.get(self.respond_url(r)).status_code, 404)
        self.assertEqual(self.client.post(self.respond_url(r), {"status": "confirmed"}).status_code, 404)
        r.refresh_from_db()
        self.assertEqual(r.status, Status.PENDING)

    def test_tampered_status_is_rejected(self):
        r = self.make_request(self.asha, self.city)
        self.login("cityrx")
        for bad in ["cancelled", "pending", "approved"]:
            with self.subTest(status=bad):
                response = self.client.post(self.respond_url(r), {"status": bad})
                self.assertEqual(response.status_code, 200)
                self.assertIn("status", response.context["form"].errors)
        r.refresh_from_db()
        self.assertEqual(r.status, Status.PENDING)

    def test_cannot_respond_twice_or_to_cancelled(self):
        for status in [Status.CONFIRMED, Status.CANCELLED]:
            with self.subTest(status=status):
                r = self.make_request(self.asha, self.city, status=status)
                self.login("cityrx")
                response = self.client.post(self.respond_url(r), {"status": "unavailable"})
                self.assertRedirects(response, reverse("pharmacy_requests"))
                r.refresh_from_db()
                self.assertEqual(r.status, status)

    def test_customer_cannot_respond(self):
        r = self.make_request(self.asha, self.city)
        self.login("asha")
        self.assertEqual(self.client.post(self.respond_url(r), {"status": "confirmed"}).status_code, 403)
        self.assertEqual(self.client.get(reverse("pharmacy_requests")).status_code, 403)

    def test_rejected_pharmacy_cannot_see_or_respond(self):
        r = self.make_request(self.asha, self.city)
        self.city.status = Pharmacy.Status.REJECTED
        self.city.save()
        self.login("cityrx")
        self.assertEqual(self.client.get(reverse("pharmacy_requests")).status_code, 403)
        self.assertEqual(self.client.post(self.respond_url(r), {"status": "confirmed"}).status_code, 403)

    def test_contact_phone_visible_to_that_pharmacy_only(self):
        self.make_request(self.asha, self.city, contact_phone="9876500000")
        self.login("cityrx")
        self.assertContains(self.client.get(reverse("pharmacy_requests")), "9876500000")
        self.client.logout()
        self.login("townrx")
        self.assertNotContains(self.client.get(reverse("pharmacy_requests"), {"show": "all"}), "9876500000")


class DashboardAndButtonTests(RequestTestBase):
    def test_pharmacy_dashboard_shows_pending_count(self):
        self.make_request(self.asha, self.city)
        self.login("cityrx")
        self.assertContains(self.client.get(reverse("pharmacy_dashboard")), "1 pending request")

    def test_customer_dashboard_shows_recent_requests(self):
        self.make_request(self.asha, self.city)
        self.login("asha")
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Recent requests")
        self.assertContains(response, "City Pharmacy")

    def test_ask_button_shown_to_customers_and_visitors_not_pharmacies(self):
        url = reverse("search")
        ask = reverse("request_create", args=[self.town_item.pk])
        self.assertContains(self.client.get(url, {"q": "dolo"}), ask)  # visitor
        self.login("asha")
        self.assertContains(self.client.get(url, {"q": "dolo"}), ask)  # customer
        self.client.logout()
        self.login("cityrx")
        self.assertNotContains(self.client.get(url, {"q": "dolo"}), ask)  # pharmacy
