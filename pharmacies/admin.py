"""Admin pages for reviewing and approving pharmacies."""

from django.contrib import admin

from .models import Pharmacy


@admin.register(Pharmacy)
class PharmacyAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "licence_number", "phone", "status", "location_set", "created_at")
    list_filter = ("status",)  # sidebar filter: Pending / Approved / Rejected
    search_fields = ("name", "licence_number", "owner__username")
    actions = ["approve_selected", "reject_selected"]

    def has_add_permission(self, request):
        # Pharmacies are created only through pharmacy sign-up, which also
        # creates the owner account with the right role. This hides the
        # admin's "Add pharmacy" button and blocks its URL.
        return False

    # boolean=True makes the admin show a green tick or red cross.
    @admin.display(boolean=True, description="Location set")
    def location_set(self, obj):
        return obj.has_location

    # Admin actions appear in the "Action" dropdown above the list.
    # Only staff users who can change pharmacies are allowed to run them.
    @admin.action(description="Approve selected pharmacies", permissions=["change"])
    def approve_selected(self, request, queryset):
        count = queryset.update(status=Pharmacy.Status.APPROVED)
        self.message_user(request, f"{count} pharmacy(ies) approved.")

    @admin.action(description="Reject selected pharmacies", permissions=["change"])
    def reject_selected(self, request, queryset):
        count = queryset.update(status=Pharmacy.Status.REJECTED)
        self.message_user(request, f"{count} pharmacy(ies) rejected.")
