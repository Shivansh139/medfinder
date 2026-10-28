"""Views for pharmacy users, and the public pharmacy detail page."""

from django.contrib import messages
from django.db.models import Case, When
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from accounts.models import User

from .forms import LocationForm, PharmacyProfileForm
from .models import Pharmacy
from .utils import haversine_km, resolve_location


@role_required(User.Role.PHARMACY)
def pharmacy_dashboard(request):
    """Show the logged-in pharmacy its approval status. Pharmacy users only."""
    # A user only ever sees their own pharmacy: we look it up by request.user.
    # .first() returns None (instead of crashing) if no pharmacy record exists.
    pharmacy = Pharmacy.objects.filter(owner=request.user).first()
    context = {"pharmacy": pharmacy}
    if pharmacy:
        # Numbers for the "Inventory" summary card.
        context["stock_total"] = pharmacy.inventory.count()
        context["stock_out"] = pharmacy.inventory.filter(quantity=0).count()
        # Number for the "Customer requests" card.
        context["pending_requests"] = pharmacy.availability_requests.filter(status="pending").count()
    return render(request, "pharmacies/dashboard.html", context)


@role_required(User.Role.PHARMACY)
def pharmacy_profile(request):
    """Let the logged-in pharmacy edit its own profile and map location."""
    # No id in the URL: the pharmacy is always the one owned by request.user,
    # so nobody can edit another pharmacy by changing the address bar.
    pharmacy = get_object_or_404(Pharmacy, owner=request.user)

    if request.method == "POST":
        # instance=pharmacy means "update this record" instead of creating a new one.
        form = PharmacyProfileForm(request.POST, instance=pharmacy)
        if form.is_valid():
            form.save()
            messages.success(request, "Your pharmacy profile has been updated.")
            return redirect("pharmacy_dashboard")
    else:
        form = PharmacyProfileForm(instance=pharmacy)

    return render(request, "pharmacies/profile_form.html", {"form": form, "pharmacy": pharmacy})


def pharmacy_detail(request, pk):
    """
    Public page for one pharmacy. Anyone can view it, but ONLY approved
    pharmacies: pending or rejected ones give 404, as if they did not exist.
    """
    pharmacy = get_object_or_404(Pharmacy, pk=pk, status=Pharmacy.Status.APPROVED)

    # Distance from the customer, if the search page passed their location on.
    location_form = LocationForm(request.GET)
    location_form.is_valid()
    location = resolve_location(location_form.cleaned_data)
    distance_km = None
    if pharmacy.has_location:
        distance_km = haversine_km(location["lat"], location["lng"], pharmacy.latitude, pharmacy.longitude)

    # In-stock medicines first (quantity 0 sorts last), then by name.
    items = pharmacy.inventory.select_related("medicine").order_by(
        Case(When(quantity=0, then=1), default=0), "medicine__name"
    )

    return render(request, "pharmacies/detail.html", {
        "pharmacy": pharmacy,
        "items": items,
        "location": location,
        "distance_km": distance_km,
    })
