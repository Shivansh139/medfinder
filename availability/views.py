"""Views for availability requests (customers ask, pharmacies answer)."""

from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from medicines.models import InventoryItem
from medicines.views import get_own_pharmacy
from pharmacies.models import Pharmacy

from .forms import RequestForm, RespondForm
from .models import AvailabilityRequest

Status = AvailabilityRequest.Status


# ---------------------------------------------------------------------------
# Customer side
# ---------------------------------------------------------------------------

@role_required(User.Role.CUSTOMER)
def request_create(request, item_pk):
    """Ask a pharmacy about one medicine it lists. Customers only."""
    # Only items of APPROVED pharmacies can be requested; anything else is 404.
    item = get_object_or_404(
        InventoryItem.objects.select_related("pharmacy", "medicine"),
        pk=item_pk,
        pharmacy__status=Pharmacy.Status.APPROVED,
    )

    # Friendly check for a duplicate (the database also blocks it).
    existing = AvailabilityRequest.objects.filter(
        customer=request.user, pharmacy=item.pharmacy, medicine=item.medicine, status=Status.PENDING
    ).first()
    if existing:
        messages.info(request, f"You already have a pending request for {item.medicine} at {item.pharmacy}.")
        return redirect("my_requests")

    if request.method == "POST":
        form = RequestForm(request.POST)
        if form.is_valid():
            availability_request = form.save(commit=False)
            # Set on the server from the logged-in user and the URL, never from the form.
            availability_request.customer = request.user
            availability_request.pharmacy = item.pharmacy
            availability_request.medicine = item.medicine
            availability_request.save()
            messages.success(request, f"Request sent to {item.pharmacy}. Their answer will appear here.")
            return redirect("my_requests")
    else:
        form = RequestForm()

    return render(request, "availability/request_form.html", {"form": form, "item": item})


@role_required(User.Role.CUSTOMER)
def my_requests(request):
    """The customer's own requests only."""
    requests_qs = (
        AvailabilityRequest.objects
        .filter(customer=request.user)
        .select_related("pharmacy", "medicine")
    )
    page_obj = Paginator(requests_qs, 20).get_page(request.GET.get("page"))
    return render(request, "availability/my_requests.html", {"page_obj": page_obj})


@role_required(User.Role.CUSTOMER)
@require_POST  # a GET (e.g. just opening the link) gives 405 and changes nothing
def request_cancel(request, pk):
    # Loaded through the customer: someone else's request gives 404.
    availability_request = get_object_or_404(AvailabilityRequest, pk=pk, customer=request.user)
    if not availability_request.is_pending:
        messages.error(request, "Only pending requests can be cancelled.")
    else:
        availability_request.status = Status.CANCELLED
        availability_request.save()
        messages.success(request, "Request cancelled.")
    return redirect("my_requests")


# ---------------------------------------------------------------------------
# Pharmacy side
# ---------------------------------------------------------------------------

@role_required(User.Role.PHARMACY)
def pharmacy_requests(request):
    """Requests sent to the logged-in user's pharmacy only."""
    pharmacy = get_own_pharmacy(request)  # 404 if none, 403 if rejected
    all_requests = pharmacy.availability_requests.select_related("customer", "medicine")

    show_all = request.GET.get("show") == "all"
    shown = all_requests if show_all else all_requests.filter(status=Status.PENDING)
    page_obj = Paginator(shown, 20).get_page(request.GET.get("page"))

    return render(request, "availability/pharmacy_requests.html", {
        "pharmacy": pharmacy,
        "page_obj": page_obj,
        "show_all": show_all,
        "pending_count": all_requests.filter(status=Status.PENDING).count(),
    })


@role_required(User.Role.PHARMACY)
def request_respond(request, pk):
    """Confirm or decline one pending request."""
    pharmacy = get_own_pharmacy(request)
    # Loaded through the pharmacy: another pharmacy's request gives 404.
    availability_request = get_object_or_404(
        AvailabilityRequest.objects.select_related("customer", "medicine"), pk=pk, pharmacy=pharmacy
    )
    if not availability_request.is_pending:
        messages.error(request, "This request has already been answered or cancelled.")
        return redirect("pharmacy_requests")

    if request.method == "POST":
        form = RespondForm(request.POST, instance=availability_request)
        if form.is_valid():
            answered = form.save(commit=False)
            answered.responded_at = timezone.now()
            answered.save()
            messages.success(request, f"Answer sent: {answered.get_status_display()}.")
            return redirect("pharmacy_requests")
    else:
        form = RespondForm(instance=availability_request)

    return render(request, "availability/respond_form.html", {
        "form": form,
        "availability_request": availability_request,
    })
