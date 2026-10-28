"""User model for MediFind."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Django's built-in user (username, email, password, is_staff, ...)
    plus one extra field: the user's role in MediFind.
    """

    class Role(models.TextChoices):
        # Value stored in the database, then the label shown to people.
        CUSTOMER = "customer", "Customer"
        PHARMACY = "pharmacy", "Pharmacy"
        ADMIN = "admin", "Administrator"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)

    def save(self, *args, **kwargs):
        # Superusers (created with `createsuperuser`) are always administrators.
        if self.is_superuser:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

    # Small helpers so views and templates can write `user.is_pharmacy`.
    @property
    def is_customer(self):
        return self.role == self.Role.CUSTOMER

    @property
    def is_pharmacy(self):
        return self.role == self.Role.PHARMACY

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN
