"""Tests for the public medicine search (Phase 5). Run with: python manage.py test"""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from pharmacies.models import Pharmacy

from .models import InventoryItem, Medicine

# Rajwada, the default "Near" location.
RAJWADA = (22.7186, 75.8553)


def make_pharmacy(username, name, status=Pharmacy.Status.APPROVED, lat=None, lng=None):
    user = User.objects.create_user(username, password="Str0ng-Test-Pass!", role=User.Role.PHARMACY)
    return Pharmacy.objects.create(
        owner=user, name=name, licence_number=f"LIC-{username}", address="Indore",
        phone="9000000000", status=status, latitude=lat, longitude=lng,
    )


class SearchTests(TestCase):
    url = reverse("search")

    def setUp(self):
        self.dolo = Medicine.objects.create(
            name="Dolo 650", brand="Micro Labs", active_ingredient="Paracetamol",
            strength="650 mg", form=Medicine.Form.TABLET, category=Medicine.Category.PAIN_FEVER,
        )
        # "near" is about 0.5 km from Rajwada, "far" about 8 km.
        self.near = make_pharmacy("near", "Near Pharmacy", lat=22.7220, lng=75.8580)
        self.far = make_pharmacy("far", "Far Pharmacy", lat=22.7900, lng=75.8800)
        self.no_location = make_pharmacy("noloc", "No Location Pharmacy")
        self.pending = make_pharmacy("pend", "Pending Pharmacy", Pharmacy.Status.PENDING, 22.72, 75.86)
        self.rejected = make_pharmacy("rej", "Rejected Pharmacy", Pharmacy.Status.REJECTED, 22.72, 75.86)

        for pharmacy, quantity, price in [
            (self.near, 10, 40), (self.far, 5, 25), (self.no_location, 3, 30),
            (self.pending, 9, 10), (self.rejected, 9, 10),
        ]:
            InventoryItem.objects.create(pharmacy=pharmacy, medicine=self.dolo, quantity=quantity, price=price)

    def result_pharmacies(self, **params):
        response = self.client.get(self.url, params)
        return [item.pharmacy.name for item in response.context["page_obj"]]

    # --- Basic search ---

    def test_empty_search_shows_suggestions_not_results(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["result_count"], 0)
        self.assertContains(response, "For example")

    def test_search_is_case_insensitive_and_matches_generic_name(self):
        for query in ["DOLO", "dolo", "Dolo 650", "paraCETAMOL", "micro labs"]:
            with self.subTest(query=query):
                self.assertIn("Near Pharmacy", self.result_pharmacies(q=query))

    def test_only_approved_pharmacies_are_shown(self):
        response = self.client.get(self.url, {"q": "dolo", "availability": "all"})
        self.assertNotContains(response, "Pending Pharmacy")
        self.assertNotContains(response, "Rejected Pharmacy")
        self.assertEqual(response.context["result_count"], 3)

    def test_no_match_shows_message(self):
        response = self.client.get(self.url, {"q": "unknownmedicine"})
        self.assertContains(response, "No approved pharmacy matches")

    # --- Availability filter ---

    def test_out_of_stock_hidden_by_default_and_shown_with_all(self):
        InventoryItem.objects.filter(pharmacy=self.near).update(quantity=0)
        self.assertNotIn("Near Pharmacy", self.result_pharmacies(q="dolo"))

        response = self.client.get(self.url, {"q": "dolo", "availability": "all"})
        self.assertContains(response, "Near Pharmacy")
        self.assertContains(response, "Out of stock")

    def test_tampered_filter_values_fall_back_to_defaults(self):
        InventoryItem.objects.filter(pharmacy=self.near).update(quantity=0)
        # Unknown values are ignored: availability -> in stock only, sort -> distance.
        names = self.result_pharmacies(q="dolo", availability="hacked", sort="drop", radius="999")
        self.assertNotIn("Near Pharmacy", names)
        self.assertEqual(names, ["Far Pharmacy", "No Location Pharmacy"])

    # --- Distance ---

    def test_results_sorted_nearest_first_unknown_distance_last(self):
        self.assertEqual(
            self.result_pharmacies(q="dolo"),
            ["Near Pharmacy", "Far Pharmacy", "No Location Pharmacy"],
        )

    def test_sort_by_price(self):
        self.assertEqual(
            self.result_pharmacies(q="dolo", sort="price"),
            ["Far Pharmacy", "No Location Pharmacy", "Near Pharmacy"],  # ₹25, ₹30, ₹40
        )

    def test_radius_filter_excludes_far_and_unknown_distance(self):
        self.assertEqual(self.result_pharmacies(q="dolo", radius="2"), ["Near Pharmacy"])

    def test_distance_is_shown(self):
        response = self.client.get(self.url, {"q": "dolo"})
        self.assertContains(response, "0.5 km away")
        self.assertContains(response, "distance unknown")

    def test_gps_location_is_used(self):
        # Standing right at "Far Pharmacy": it becomes the nearest.
        response = self.client.get(self.url, {"q": "dolo", "lat": "22.7900", "lng": "75.8800"})
        self.assertContains(response, "Your current location")
        self.assertEqual(response.context["page_obj"][0].pharmacy.name, "Far Pharmacy")

    def test_invalid_gps_falls_back_to_default_location(self):
        response = self.client.get(self.url, {"q": "dolo", "lat": "999", "lng": "abc"})
        self.assertContains(response, "Rajwada (centre), Indore")

    def test_preset_area_is_used(self):
        response = self.client.get(self.url, {"q": "dolo", "near": "vijay_nagar"})
        self.assertContains(response, "Distances from: <strong>Vijay Nagar, Indore</strong>", html=False)

    # --- Labels and notices ---

    def test_stale_label_only_for_old_stock(self):
        response = self.client.get(self.url, {"q": "dolo"})
        self.assertNotContains(response, "may be outdated")

        InventoryItem.objects.filter(pharmacy=self.near).update(
            last_updated=timezone.now() - timedelta(days=8)
        )
        response = self.client.get(self.url, {"q": "dolo"})
        self.assertContains(response, "may be outdated", count=1)

    def test_confirm_by_phone_notice_and_call_link(self):
        response = self.client.get(self.url, {"q": "dolo"})
        self.assertContains(response, "Please call the pharmacy to confirm before you travel")
        self.assertContains(response, 'href="tel:9000000000"')

    def test_map_data_contains_only_result_pharmacies(self):
        response = self.client.get(self.url, {"q": "dolo"})
        pins = response.context["map_data"]["pharmacies"]
        self.assertEqual({pin["name"] for pin in pins}, {"Near Pharmacy", "Far Pharmacy"})  # no-location has no pin
        self.assertContains(response, 'id="map-data"')

    def test_search_is_public(self):
        """No login needed to search."""
        self.client.logout()
        self.assertEqual(self.client.get(self.url, {"q": "dolo"}).status_code, 200)
