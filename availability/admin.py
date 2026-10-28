"""Admin page for availability requests (mainly for checking data)."""

from django.contrib import admin

from .models import AvailabilityRequest


@admin.register(AvailabilityRequest)
class AvailabilityRequestAdmin(admin.ModelAdmin):
    list_display = ("medicine", "pharmacy", "customer", "quantity", "status", "created_at", "responded_at")
    list_filter = ("status", "pharmacy")
    search_fields = ("medicine__name", "pharmacy__name", "customer__username")
    list_select_related = ("medicine", "pharmacy", "customer")
    readonly_fields = ("created_at", "updated_at", "responded_at")
