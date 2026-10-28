"""Show our custom User in the Django admin site."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Reuse Django's user admin and add the "role" field to it.
    list_display = ("username", "email", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    fieldsets = UserAdmin.fieldsets + (("MediFind", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("MediFind", {"fields": ("role",)}),)
