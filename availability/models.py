"""Availability requests: a customer asks a pharmacy to confirm a medicine is in stock."""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from medicines.models import Medicine
from pharmacies.models import Pharmacy


class AvailabilityRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"                # waiting for the pharmacy
        CONFIRMED = "confirmed", "Confirmed"          # pharmacy: "yes, we have it"
        UNAVAILABLE = "unavailable", "Unavailable"    # pharmacy: "sorry, we don't"
        CANCELLED = "cancelled", "Cancelled"          # customer withdrew the request

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="availability_requests"
    )
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE, related_name="availability_requests")
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT, related_name="availability_requests")

    quantity = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    note = models.CharField(max_length=200, blank=True)  # optional message from the customer
    # Optional number the pharmacy can call back on. Shown only to that pharmacy
    # (and to the customer who wrote it).
    contact_phone = models.CharField(max_length=20, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    pharmacy_reply = models.CharField(max_length=200, blank=True)  # optional answer from the pharmacy

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    responded_at = models.DateTimeField(null=True, blank=True)  # when the pharmacy answered

    class Meta:
        ordering = ["-created_at"]  # newest first
        constraints = [
            # At most ONE pending request per customer + pharmacy + medicine.
            # "condition" means the rule only applies to pending rows, so a new
            # request is allowed once the old one is answered or cancelled.
            models.UniqueConstraint(
                fields=["customer", "pharmacy", "medicine"],
                condition=models.Q(status="pending"),
                name="one_pending_request_per_medicine",
            ),
        ]

    def __str__(self):
        return f"{self.customer} → {self.pharmacy}: {self.medicine} ({self.get_status_display()})"

    @property
    def is_pending(self):
        # Only pending requests can still change (be answered or cancelled).
        return self.status == self.Status.PENDING

    @property
    def badge_class(self):
        """Bootstrap colour for the status badge."""
        return {
            self.Status.PENDING: "text-bg-warning",
            self.Status.CONFIRMED: "text-bg-success",
            self.Status.UNAVAILABLE: "text-bg-danger",
            self.Status.CANCELLED: "text-bg-secondary",
        }[self.status]
