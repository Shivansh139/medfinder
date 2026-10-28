"""Tests for the medicine catalogue, inventory and demo data. Run with: python manage.py test"""

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from availability.models import AvailabilityRequest
from pharmacies.models import Pharmacy

from .models import InventoryItem, Medicine

PASSWORD = "Str0ng-Test-Pass!"


def make_pharmacy(username, licence, status=Pharmacy.Status.APPROVED):
    user = User.objects.create_user(username, password=PASSWORD, role=User.Role.PHARMACY)
    pharmacy = Pharmacy.objects.create(
        owner=user, name=f"{username} pharmacy", licence_number=licence,
        address="Somewhere", phone="9000000000", status=status,
    )
    return pharmacy


def make_medicine(name="Dolo 650", strength="650 mg"):
    return Medicine.objects.create(
        name=name, brand="Micro Labs", active_ingredient="Paracetamol",
        strength=strength, form=Medicine.Form.TABLET, category=Medicine.Category.PAIN_FEVER,
    )


class ModelRuleTests(TestCase):
    def setUp(self):
        self.pharmacy = make_pharmacy("cityrx", "LIC-1")
        self.medicine = make_medicine()

    def test_zero_quantity_means_unavailable(self):
        item = InventoryItem.objects.create(pharmacy=self.pharmacy, medicine=self.medicine, quantity=0, price=30)
        self.assertFalse(item.is_available)
        item.quantity = 1
        self.assertTrue(item.is_available)

    def test_database_blocks_duplicate_pharmacy_medicine(self):
        InventoryItem.objects.create(pharmacy=self.pharmacy, medicine=self.medicine, quantity=5, price=30)
        with self.assertRaises(IntegrityError), transaction.atomic():
            InventoryItem.objects.create(pharmacy=self.pharmacy, medicine=self.medicine, quantity=9, price=31)

    def test_database_blocks_duplicate_medicine(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_medicine()  # same name + strength + form again

    def test_medicine_in_stock_cannot_be_deleted(self):
        InventoryItem.objects.create(pharmacy=self.pharmacy, medicine=self.medicine, quantity=5, price=30)
        with self.assertRaises(ProtectedError):
            self.medicine.delete()


class InventoryPermissionTests(TestCase):
    """Only the owning pharmacy can see or change its inventory."""

    def setUp(self):
        self.mine = make_pharmacy("cityrx", "LIC-1")
        self.other = make_pharmacy("townrx", "LIC-2")
        medicine = make_medicine()
        self.other_item = InventoryItem.objects.create(pharmacy=self.other, medicine=medicine, quantity=7, price=30)

    def test_logged_out_visitor_is_sent_to_login(self):
        url = reverse("inventory_list")
        self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}")

    def test_customer_gets_403(self):
        User.objects.create_user("asha", password=PASSWORD, role=User.Role.CUSTOMER)
        self.client.login(username="asha", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("inventory_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("inventory_add")).status_code, 403)

    def test_other_pharmacys_item_is_404_for_edit_and_delete(self):
        self.client.login(username="cityrx", password=PASSWORD)
        edit_url = reverse("inventory_edit", args=[self.other_item.pk])
        delete_url = reverse("inventory_delete", args=[self.other_item.pk])

        self.assertEqual(self.client.get(edit_url).status_code, 404)
        self.assertEqual(self.client.post(edit_url, {"quantity": 0, "price": 1}).status_code, 404)
        self.assertEqual(self.client.get(delete_url).status_code, 404)
        self.assertEqual(self.client.post(delete_url).status_code, 404)

        # Nothing changed.
        self.other_item.refresh_from_db()
        self.assertEqual(self.other_item.quantity, 7)

    def test_list_shows_only_own_items(self):
        self.client.login(username="cityrx", password=PASSWORD)
        response = self.client.get(reverse("inventory_list"))
        self.assertNotContains(response, "Dolo 650")
        self.assertContains(response, "Your inventory is empty")

    def test_rejected_pharmacy_cannot_manage_inventory(self):
        self.mine.status = Pharmacy.Status.REJECTED
        self.mine.save()
        self.client.login(username="cityrx", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("inventory_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("inventory_add")).status_code, 403)

    def test_pending_pharmacy_can_manage_inventory(self):
        self.mine.status = Pharmacy.Status.PENDING
        self.mine.save()
        self.client.login(username="cityrx", password=PASSWORD)
        response = self.client.get(reverse("inventory_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "once an administrator approves")


class InventoryManagementTests(TestCase):
    def setUp(self):
        self.pharmacy = make_pharmacy("cityrx", "LIC-1")
        self.dolo = make_medicine()
        self.crocin = make_medicine("Crocin Advance", "500 mg")
        self.client.login(username="cityrx", password=PASSWORD)

    def test_add_item_is_saved_for_own_pharmacy(self):
        response = self.client.post(reverse("inventory_add"), {
            "medicine": self.dolo.pk, "quantity": 30, "price": "32.50",
        })
        self.assertRedirects(response, reverse("inventory_list"))
        item = InventoryItem.objects.get()
        self.assertEqual(item.pharmacy, self.pharmacy)
        self.assertEqual(item.quantity, 30)

    def test_tampered_pharmacy_field_is_ignored(self):
        other = make_pharmacy("townrx", "LIC-2")
        self.client.post(reverse("inventory_add"), {
            "medicine": self.dolo.pk, "quantity": 30, "price": "32.50", "pharmacy": other.pk,
        })
        self.assertEqual(InventoryItem.objects.get().pharmacy, self.pharmacy)

    def test_duplicate_medicine_is_rejected(self):
        InventoryItem.objects.create(pharmacy=self.pharmacy, medicine=self.dolo, quantity=5, price=30)
        response = self.client.post(reverse("inventory_add"), {
            "medicine": self.dolo.pk, "quantity": 9, "price": 31,
        })
        self.assertEqual(response.status_code, 200)  # form shown again
        self.assertContains(response, "Select a valid choice")
        self.assertEqual(InventoryItem.objects.count(), 1)

    def test_add_form_only_offers_medicines_not_yet_stocked(self):
        InventoryItem.objects.create(pharmacy=self.pharmacy, medicine=self.dolo, quantity=5, price=30)
        form = self.client.get(reverse("inventory_add")).context["form"]
        self.assertEqual(list(form.fields["medicine"].queryset), [self.crocin])

    def test_negative_quantity_and_price_are_rejected(self):
        response = self.client.post(reverse("inventory_add"), {
            "medicine": self.dolo.pk, "quantity": -1, "price": -5,
        })
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("quantity", form.errors)
        self.assertIn("price", form.errors)
        self.assertFalse(InventoryItem.objects.exists())

    def test_edit_changes_quantity_and_price_but_not_medicine(self):
        item = InventoryItem.objects.create(pharmacy=self.pharmacy, medicine=self.dolo, quantity=5, price=30)
        response = self.client.post(reverse("inventory_edit", args=[item.pk]), {
            "quantity": 0, "price": "35.00", "medicine": self.crocin.pk,  # medicine is tampered
        })
        self.assertRedirects(response, reverse("inventory_list"))
        item.refresh_from_db()
        self.assertEqual(item.quantity, 0)
        self.assertEqual(str(item.price), "35.00")
        self.assertEqual(item.medicine, self.dolo)

    def test_zero_stock_shows_out_of_stock_badge(self):
        InventoryItem.objects.create(pharmacy=self.pharmacy, medicine=self.dolo, quantity=0, price=30)
        InventoryItem.objects.create(pharmacy=self.pharmacy, medicine=self.crocin, quantity=4, price=20)
        response = self.client.get(reverse("inventory_list"))
        self.assertContains(response, "Out of stock", count=2)  # summary label + one badge
        self.assertContains(response, "In stock", count=1)
        self.assertEqual(response.context["out_of_stock_count"], 1)

    def test_search_filters_inventory(self):
        InventoryItem.objects.create(pharmacy=self.pharmacy, medicine=self.dolo, quantity=3, price=30)
        InventoryItem.objects.create(pharmacy=self.pharmacy, medicine=self.crocin, quantity=4, price=20)
        response = self.client.get(reverse("inventory_list"), {"q": "crocin"})
        self.assertEqual([i.medicine for i in response.context["page_obj"]], [self.crocin])

    def test_delete_needs_post(self):
        item = InventoryItem.objects.create(pharmacy=self.pharmacy, medicine=self.dolo, quantity=5, price=30)
        url = reverse("inventory_delete", args=[item.pk])

        response = self.client.get(url)  # GET only shows the confirmation page
        self.assertContains(response, "Remove from inventory?")
        self.assertTrue(InventoryItem.objects.filter(pk=item.pk).exists())

        response = self.client.post(url)
        self.assertRedirects(response, reverse("inventory_list"))
        self.assertFalse(InventoryItem.objects.filter(pk=item.pk).exists())

    def test_dashboard_shows_stock_summary(self):
        InventoryItem.objects.create(pharmacy=self.pharmacy, medicine=self.dolo, quantity=0, price=30)
        response = self.client.get(reverse("pharmacy_dashboard"))
        self.assertContains(response, "1 medicine")
        self.assertContains(response, "1 out of stock")


class DemoDataTests(TestCase):
    def test_fixture_loads(self):
        call_command("loaddata", "medicines", verbosity=0)
        self.assertGreaterEqual(Medicine.objects.count(), 30)

    def test_seed_demo_creates_pharmacies_and_can_run_twice(self):
        for _ in range(2):  # running again must not create duplicates
            call_command("seed_demo", password=PASSWORD, stdout=StringIO())

        self.assertEqual(Pharmacy.objects.count(), 4)
        self.assertEqual(Pharmacy.objects.filter(status=Pharmacy.Status.PENDING).count(), 1)
        self.assertTrue(InventoryItem.objects.filter(quantity=0).exists())  # some out of stock
        # Every demo pharmacy has a map location and can log in with the given password.
        self.assertFalse(Pharmacy.objects.filter(latitude__isnull=True).exists())
        self.assertTrue(self.client.login(username="demo_sanjeevani", password=PASSWORD))
        # Demo customer with one request in each status, not duplicated by the second run.
        self.assertTrue(self.client.login(username="demo_patient", password=PASSWORD))
        requests = AvailabilityRequest.objects.filter(customer__username="demo_patient")
        self.assertEqual(requests.count(), 5)
        self.assertEqual(set(requests.values_list("status", flat=True)),
                         {"pending", "confirmed", "unavailable", "cancelled"})
        # Some stock is "stale" for the demo label.
        self.assertTrue(any(item.is_stale for item in InventoryItem.objects.all()))

    def test_seed_demo_rejects_weak_password(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo", password="123", stdout=StringIO())
        self.assertFalse(Pharmacy.objects.exists())
