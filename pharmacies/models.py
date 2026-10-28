"""Pharmacy model for MediFind."""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Pharmacy(models.Model):
    """A pharmacy registered by a pharmacy user. Admins must approve it."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    # Each pharmacy belongs to exactly one user account (and vice versa).
    # settings.AUTH_USER_MODEL points to accounts.User.
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,  # deleting the user deletes their pharmacy
        related_name="pharmacy",   # lets us write user.pharmacy
    )
    name = models.CharField(max_length=200)
    licence_number = models.CharField(max_length=50, unique=True)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    # Optional free text, e.g. "9 am – 9 pm, closed Sunday".
    opening_hours = models.CharField(max_length=100, blank=True)

    # Home delivery. The profile form requires the phone when delivery is on.
    home_delivery_available = models.BooleanField(default=False)
    home_delivery_phone = models.CharField(max_length=20, blank=True)

    # Map location, set by the pharmacy on its profile page. Blank until then.
    # Validators make the server reject impossible coordinates.
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )

    # New registrations start as "pending" until an admin reviews them.
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]  # newest first
        verbose_name_plural = "pharmacies"

    def __str__(self):
        return self.name

    @property
    def is_approved(self):
        return self.status == self.Status.APPROVED

    @property
    def has_location(self):
        return self.latitude is not None and self.longitude is not None
