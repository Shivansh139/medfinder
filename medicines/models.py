"""Medicine catalogue and pharmacy inventory."""

from datetime import timedelta

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from pharmacies.models import Pharmacy


class Medicine(models.Model):
    """
    One medicine in the shared catalogue, e.g. "Dolo 650, 650 mg tablet".
    Only administrators add medicines (in the admin site); pharmacies pick
    from this list, so every pharmacy uses the same names.
    """

    class Form(models.TextChoices):
        TABLET = "tablet", "Tablet"
        CAPSULE = "capsule", "Capsule"
        SYRUP = "syrup", "Syrup"
        INJECTION = "injection", "Injection"
        CREAM = "cream", "Cream / ointment"
        DROPS = "drops", "Drops"
        INHALER = "inhaler", "Inhaler"
        OTHER = "other", "Other"

    class Category(models.TextChoices):
        PAIN_FEVER = "pain_fever", "Pain & fever"
        ANTIBIOTIC = "antibiotic", "Antibiotic"
        DIABETES = "diabetes", "Diabetes"
        HEART_BP = "heart_bp", "Heart & blood pressure"
        ALLERGY = "allergy", "Allergy & cold"
        BREATHING = "breathing", "Breathing & cough"
        STOMACH = "stomach", "Stomach & digestion"
        VITAMINS = "vitamins", "Vitamins & supplements"
        SKIN = "skin", "Skin"
        OTHER = "other", "Other"

    name = models.CharField(max_length=150, help_text="Name printed on the pack, e.g. Dolo 650")
    brand = models.CharField(max_length=100, help_text="Manufacturer, e.g. Micro Labs")
    active_ingredient = models.CharField(max_length=150, help_text="Generic name, e.g. Paracetamol")
    strength = models.CharField(max_length=50, help_text="e.g. 650 mg")
    form = models.CharField(max_length=20, choices=Form.choices)
    category = models.CharField(max_length=20, choices=Category.choices)

    class Meta:
        ordering = ["name"]
        constraints = [
            # The database refuses a second "Dolo 650, 650 mg, tablet".
            models.UniqueConstraint(
                fields=["name", "strength", "form"], name="unique_medicine_name_strength_form"
            ),
        ]

    def __str__(self):
        return f"{self.name} {self.strength} ({self.get_form_display()})"


class InventoryItem(models.Model):
    """How many of one medicine one pharmacy has, and at what price."""

    # Stock not updated for this many days is shown to customers as "may be outdated".
    STALE_AFTER_DAYS = 7

    pharmacy = models.ForeignKey(
        Pharmacy, on_delete=models.CASCADE, related_name="inventory"  # pharmacy.inventory
    )
    # PROTECT: a medicine that some pharmacy stocks cannot be deleted from the catalogue.
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT, related_name="inventory_items")
    # PositiveIntegerField allows 0 and up. 0 means "out of stock".
    quantity = models.PositiveIntegerField(default=0)
    # Price in rupees (₹), e.g. 32.50
    price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    last_updated = models.DateTimeField(auto_now=True)  # set automatically on every save

    class Meta:
        ordering = ["medicine__name"]
        constraints = [
            # Each pharmacy has at most one row per medicine.
            models.UniqueConstraint(fields=["pharmacy", "medicine"], name="unique_pharmacy_medicine"),
        ]

    def __str__(self):
        return f"{self.medicine} at {self.pharmacy}"

    @property
    def is_available(self):
        """Zero quantity means the medicine is unavailable at this pharmacy."""
        return self.quantity > 0

    @property
    def is_stale(self):
        """True if the pharmacy has not updated this stock for STALE_AFTER_DAYS days."""
        return self.last_updated < timezone.now() - timedelta(days=self.STALE_AFTER_DAYS)
