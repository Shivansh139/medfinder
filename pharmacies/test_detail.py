"""Tests for distance calculation and the public pharmacy page (Phase 5)."""

from datetime import timedelta

from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from medicines.models import InventoryItem, Medicine

from .models import Pharmacy
from .utils import haversine_km


class HaversineTests(SimpleTestCase):
    def test_same_point_is_zero(self):
        self.assertAlmostEqual(haversine_km(22.7186, 75.8553, 22.7186, 75.8553), 0)

    def test_one_degree_of_longitude_at_equator(self):
        # Circumference 2π × 6371 km / 360 degrees ≈ 111.19 km per degree.
        self.assertAlmostEqual(haversine_km(0, 0, 0, 1), 111.19, places=2)

    def test_distance_is_the_same_both_ways(self):
        a = haversine_km(22.7186, 75.8553, 22.7533, 75.8937)
        b = haversine_km(22.7533, 75.8937, 22.7186, 75.8553)
        self.assertAlmostEqual(a, b)
        self.assertAlmostEqual(a, 5.5, delta=0.2)  # Rajwada to Vijay Nagar is about 5.5 km


class PharmacyDetailTests(TestCase):
    def setUp(self):
        user = User.objects.create_user("cityrx", password="Str0ng-Test-Pass!", role=User.Role.PHARMACY)
        self.pharmacy = Pharmacy.objects.create(
            owner=user, name="City Pharmacy", licence_number="LIC-1", address="12 MG Road",
            phone="9000000001", status=Pharmacy.Status.APPROVED, latitude=22.7220, longitude=75.8580,
        )
        medicine = Medicine.objects.create(
            name="Dolo 650", brand="Micro Labs", active_ingredient="Paracetamol",
            strength="650 mg", form=Medicine.Form.TABLET, category=Medicine.Category.PAIN_FEVER,
        )
        self.item = InventoryItem.objects.create(pharmacy=self.pharmacy, medicine=medicine, quantity=4, price=30)
        self.url = reverse("pharmacy_detail", args=[self.pharmacy.pk])

    def test_approved_pharmacy_page_is_public(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "City Pharmacy")
        self.assertContains(response, "Dolo 650")
        self.assertContains(response, 'href="tel:9000000001"')
        self.assertContains(response, "google.com/maps/dir/")
        self.assertContains(response, "Please call the pharmacy to confirm")

    def test_pending_and_rejected_pharmacies_are_404(self):
        for status in [Pharmacy.Status.PENDING, Pharmacy.Status.REJECTED]:
            with self.subTest(status=status):
                self.pharmacy.status = status
                self.pharmacy.save()
                self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_delivery_button_only_when_delivery_enabled(self):
        self.assertNotContains(self.client.get(self.url), "Call for Home Delivery")

        self.pharmacy.home_delivery_available = True
        self.pharmacy.home_delivery_phone = "9000000099"
        self.pharmacy.save()
        response = self.client.get(self.url)
        self.assertContains(response, "Call for Home Delivery")
        self.assertContains(response, 'href="tel:9000000099"')

    def test_distance_from_chosen_area(self):
        response = self.client.get(self.url, {"near": "rajwada"})
        self.assertContains(response, "0.5 km from Rajwada (centre), Indore")

    def test_stale_label_on_detail_page(self):
        InventoryItem.objects.filter(pk=self.item.pk).update(last_updated=timezone.now() - timedelta(days=12))
        self.assertContains(self.client.get(self.url), "may be outdated")
