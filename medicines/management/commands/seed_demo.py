"""
Create demo data for presenting MediFind.

Usage:
    python manage.py seed_demo --password "<a password you choose>"

What it creates (safe to run more than once; it updates instead of duplicating):
  * the medicine catalogue (from medicines/fixtures/medicines.json)
  * 4 demo pharmacies in Indore with map locations, each with its own login
    (3 approved, 1 pending so you can demo approval), and their stock
    (some items at quantity 0 to demo "out of stock", and 3 per pharmacy
    last updated 10-20 days ago to demo the "may be outdated" label).
  * a demo customer, demo_patient, with availability requests in every
    status (pending, confirmed, unavailable, cancelled).
  All pharmacies, stock and prices are fictional.

The password is given on the command line, so it is never stored in the code.
All demo accounts (pharmacies and demo_patient) get this password. Running again resets it.
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from availability.models import AvailabilityRequest
from medicines.models import InventoryItem, Medicine
from pharmacies.models import Pharmacy

# username, pharmacy name, licence, address, phone, lat, lng, status, delivery phone ("" = none)
DEMO_PHARMACIES = [
    ("demo_sanjeevani", "Sanjeevani Medicals", "DEMO-IND-001",
     "Scheme 54, Vijay Nagar, Indore", "9000000101",
     "22.753300", "75.893700", Pharmacy.Status.APPROVED, "9000000111"),
    ("demo_shreekrishna", "Shree Krishna Pharmacy", "DEMO-IND-002",
     "Near Rajwada, Indore", "9000000102",
     "22.718600", "75.855300", Pharmacy.Status.APPROVED, ""),
    ("demo_narmada", "Narmada Medical Store", "DEMO-IND-003",
     "Old Palasia, Indore", "9000000103",
     "22.724400", "75.883900", Pharmacy.Status.APPROVED, "9000000113"),
    ("demo_arogya", "Arogya Chemists", "DEMO-IND-004",
     "Bhawarkua Square, Indore", "9000000104",
     "22.692600", "75.867600", Pharmacy.Status.PENDING, ""),
]

# Fixed Dolo 650 stock so the demo always shows one pharmacy that is out of stock.
DOLO_QUANTITIES = {"demo_sanjeevani": 40, "demo_shreekrishna": 0, "demo_narmada": 25, "demo_arogya": 10}


class Command(BaseCommand):
    help = "Create demo medicines, pharmacies and inventory for presentations."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password", required=True,
            help="Password for all demo accounts (choose your own).",
        )

    @transaction.atomic  # all or nothing
    def handle(self, *args, **options):
        password = options["password"]
        # Use Django's normal password rules, so no weak demo password slips in.
        try:
            validate_password(password)
        except ValidationError as error:
            raise CommandError("Password rejected: " + " ".join(error.messages))

        # 1. Medicine catalogue (loaddata updates rows that already exist).
        call_command("loaddata", "medicines", verbosity=0)
        medicines = list(Medicine.objects.all())
        self.stdout.write(f"Catalogue: {len(medicines)} medicines")

        # 2. Demo pharmacies, their owner accounts and stock.
        for index, row in enumerate(DEMO_PHARMACIES):
            username, name, licence, address, phone, lat, lng, status, delivery_phone = row

            user, _ = User.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@example.com", "role": User.Role.PHARMACY},
            )
            user.role = User.Role.PHARMACY
            user.set_password(password)  # stores a hash, never the plain password
            user.save()

            pharmacy, _ = Pharmacy.objects.update_or_create(
                owner=user,
                defaults={
                    "name": name, "licence_number": licence, "address": address, "phone": phone,
                    "latitude": Decimal(lat), "longitude": Decimal(lng), "status": status,
                    "opening_hours": "9 am – 10 pm, all days",
                    "home_delivery_available": bool(delivery_phone),
                    "home_delivery_phone": delivery_phone,
                },
            )

            # Pick about 20 medicines for this pharmacy. A fixed "seed" makes the
            # random choices the same every run, so the demo is predictable.
            rng = random.Random(index)
            chosen = rng.sample(medicines, 20)
            dolo = next(m for m in medicines if m.name == "Dolo 650")
            if dolo not in chosen:
                chosen.append(dolo)

            other_item_ids = []
            for medicine in chosen:
                if medicine == dolo:
                    quantity = DOLO_QUANTITIES[username]
                else:
                    quantity = rng.choice([0, 5, 12, 20, 35, 50, 80, 120])
                price = Decimal(rng.randrange(20, 500)).quantize(Decimal("0.01"))
                item, _ = InventoryItem.objects.update_or_create(
                    pharmacy=pharmacy, medicine=medicine,
                    defaults={"quantity": quantity, "price": price},
                )
                if medicine != dolo:
                    other_item_ids.append(item.pk)

            # Make 3 items look "stale" (not updated for 10-20 days) to demo the
            # stale-data label. .update() writes straight to the database, so
            # auto_now does not reset the date. Dolo 650 stays fresh.
            stale_ids = rng.sample(other_item_ids, 3)
            InventoryItem.objects.filter(pk__in=stale_ids).update(
                last_updated=timezone.now() - timedelta(days=rng.randint(10, 20))
            )

            self.stdout.write(
                f"  {name} ({pharmacy.get_status_display()}) - login: {username} - "
                f"{pharmacy.inventory.count()} items, {pharmacy.inventory.filter(quantity=0).count()} out of stock"
            )

        # 3. A demo customer with requests in every status, so the request
        #    screens are not empty during a demo.
        self.create_demo_requests(password)

        self.stdout.write(self.style.SUCCESS("Demo data ready."))

    def create_demo_requests(self, password):
        patient, _ = User.objects.get_or_create(
            username="demo_patient",
            defaults={"email": "demo_patient@example.com", "role": User.Role.CUSTOMER},
        )
        patient.role = User.Role.CUSTOMER
        patient.set_password(password)
        patient.save()

        # Start fresh each run (only this demo customer's requests), so running twice is safe.
        AvailabilityRequest.objects.filter(customer=patient).delete()

        def pharmacy(username):
            return Pharmacy.objects.get(owner__username=username)

        def medicine_at(pharm, position):
            """The Nth medicine (alphabetical, not Dolo 650) that this pharmacy lists."""
            items = pharm.inventory.exclude(medicine__name="Dolo 650").order_by("medicine__name")
            return items[position].medicine

        dolo = Medicine.objects.get(name="Dolo 650", strength="650 mg", form=Medicine.Form.TABLET)
        sanjeevani = pharmacy("demo_sanjeevani")
        shree_krishna = pharmacy("demo_shreekrishna")
        narmada = pharmacy("demo_narmada")
        an_hour_ago = timezone.now() - timedelta(hours=1)
        Status = AvailabilityRequest.Status

        demo_requests = [
            # pharmacy, medicine, quantity, note, phone, status, reply
            (sanjeevani, dolo, 2, "Need it by this evening.", "9000000201", Status.PENDING, ""),
            (narmada, medicine_at(narmada, 0), 1, "", "", Status.PENDING, ""),
            (narmada, medicine_at(narmada, 1), 1, "", "", Status.CONFIRMED,
             "Available. We are open till 10 pm."),
            (shree_krishna, dolo, 1, "", "9000000201", Status.UNAVAILABLE,
             "Out of stock, expected next week."),
            (sanjeevani, medicine_at(sanjeevani, 0), 1, "", "", Status.CANCELLED, ""),
        ]
        for pharm, medicine, quantity, note, phone, status, reply in demo_requests:
            AvailabilityRequest.objects.create(
                customer=patient, pharmacy=pharm, medicine=medicine, quantity=quantity,
                note=note, contact_phone=phone, status=status, pharmacy_reply=reply,
                responded_at=an_hour_ago if status in (Status.CONFIRMED, Status.UNAVAILABLE) else None,
            )

        self.stdout.write(f"  Demo customer - login: demo_patient - {len(demo_requests)} requests")
