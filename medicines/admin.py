"""Admin pages for the medicine catalogue and pharmacy inventory."""

from django.contrib import admin

from .models import InventoryItem, Medicine


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    # Administrators manage the catalogue here (add / edit / search).
    list_display = ("name", "strength", "form", "active_ingredient", "brand", "category")
    list_filter = ("form", "category")
    search_fields = ("name", "active_ingredient", "brand")


class AvailabilityFilter(admin.SimpleListFilter):
    """Sidebar filter: In stock (quantity > 0) / Out of stock (quantity = 0)."""

    title = "availability"
    parameter_name = "available"

    def lookups(self, request, model_admin):
        return [("yes", "In stock"), ("no", "Out of stock")]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(quantity__gt=0)
        if self.value() == "no":
            return queryset.filter(quantity=0)
        return queryset


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    # Mainly for checking data; pharmacies edit their own stock on the site.
    list_display = ("medicine", "pharmacy", "quantity", "price", "available", "last_updated")
    list_filter = (AvailabilityFilter, "pharmacy")
    search_fields = ("medicine__name", "medicine__active_ingredient", "pharmacy__name")
    list_select_related = ("medicine", "pharmacy")

    @admin.display(boolean=True, description="Available")
    def available(self, obj):
        return obj.is_available
