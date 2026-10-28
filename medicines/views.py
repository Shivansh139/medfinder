"""Views for pharmacies to manage their own inventory, and the public medicine search."""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.decorators import role_required
from accounts.models import User
from pharmacies.models import Pharmacy
from pharmacies.utils import haversine_km, resolve_location

from .forms import InventoryAddForm, InventoryEditForm, SearchForm
from .models import InventoryItem


def get_own_pharmacy(request):
    """
    Return the logged-in user's pharmacy, if it may manage inventory.
    - No pharmacy linked      -> 404
    - Pharmacy was rejected   -> 403
    Pending and approved pharmacies may manage inventory.
    """
    pharmacy = get_object_or_404(Pharmacy, owner=request.user)
    if pharmacy.status == Pharmacy.Status.REJECTED:
        raise PermissionDenied
    return pharmacy


def get_own_item(request, pk):
    """
    Load one inventory item, but ONLY from the user's own pharmacy.
    Another pharmacy's item gives 404, so nobody can even tell it exists.
    """
    pharmacy = get_own_pharmacy(request)
    return get_object_or_404(InventoryItem, pk=pk, pharmacy=pharmacy)


@role_required(User.Role.PHARMACY)
def inventory_list(request):
    pharmacy = get_own_pharmacy(request)
    items = pharmacy.inventory.select_related("medicine")  # select_related = fewer DB queries

    # Optional search box (?q=dolo) over name, generic name and manufacturer.
    query = request.GET.get("q", "").strip()
    if query:
        items = items.filter(
            Q(medicine__name__icontains=query)
            | Q(medicine__active_ingredient__icontains=query)
            | Q(medicine__brand__icontains=query)
        )

    # Show 25 items per page.
    page_obj = Paginator(items, 25).get_page(request.GET.get("page"))

    context = {
        "pharmacy": pharmacy,
        "page_obj": page_obj,
        "query": query,
        "total_count": pharmacy.inventory.count(),
        "out_of_stock_count": pharmacy.inventory.filter(quantity=0).count(),
    }
    return render(request, "medicines/inventory_list.html", context)


@role_required(User.Role.PHARMACY)
def inventory_add(request):
    pharmacy = get_own_pharmacy(request)

    if request.method == "POST":
        form = InventoryAddForm(request.POST, pharmacy=pharmacy)
        if form.is_valid():
            item = form.save(commit=False)
            item.pharmacy = pharmacy  # set on the server, never taken from the form
            item.save()
            messages.success(request, f"{item.medicine} added to your inventory.")
            return redirect("inventory_list")
    else:
        form = InventoryAddForm(pharmacy=pharmacy)

    return render(request, "medicines/inventory_form.html", {
        "form": form,
        "title": "Add medicine to inventory",
        "nothing_left_to_add": not form.fields["medicine"].queryset.exists(),
    })


@role_required(User.Role.PHARMACY)
def inventory_edit(request, pk):
    item = get_own_item(request, pk)

    if request.method == "POST":
        form = InventoryEditForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f"{item.medicine} updated.")
            return redirect("inventory_list")
    else:
        form = InventoryEditForm(instance=item)

    return render(request, "medicines/inventory_form.html", {
        "form": form,
        "item": item,
        "title": f"Edit {item.medicine}",
    })


@role_required(User.Role.PHARMACY)
def inventory_delete(request, pk):
    item = get_own_item(request, pk)

    # GET shows a confirmation page; only a POST (the button) deletes.
    if request.method == "POST":
        name = str(item.medicine)
        item.delete()
        messages.success(request, f"{name} removed from your inventory.")
        return redirect("inventory_list")

    return render(request, "medicines/inventory_confirm_delete.html", {"item": item})


# ---------------------------------------------------------------------------
# Public medicine search (anyone can use it, no login needed)
# ---------------------------------------------------------------------------

def search(request):
    form = SearchForm(request.GET)
    form.is_valid()  # fills form.cleaned_data with every field that is valid
    data = form.cleaned_data  # invalid/tampered fields are simply missing -> defaults below

    query = (data.get("q") or "").strip()
    only_in_stock = (data.get("availability") or "in_stock") == "in_stock"
    radius_km = int(data["radius"]) if data.get("radius") else None
    sort = data.get("sort") or "distance"
    location = resolve_location(data)  # where distances are measured from

    results = []
    if query:
        # 1. Database query: case-insensitive match (icontains), APPROVED pharmacies only.
        items = (
            InventoryItem.objects
            .filter(pharmacy__status=Pharmacy.Status.APPROVED)
            .filter(
                Q(medicine__name__icontains=query)
                | Q(medicine__active_ingredient__icontains=query)
                | Q(medicine__brand__icontains=query)
            )
            .select_related("medicine", "pharmacy")
        )
        if only_in_stock:
            items = items.filter(quantity__gt=0)

        # 2. Distance for each result, worked out in Python with the Haversine formula.
        for item in items:
            pharmacy = item.pharmacy
            if pharmacy.has_location:
                item.distance_km = haversine_km(
                    location["lat"], location["lng"], pharmacy.latitude, pharmacy.longitude
                )
            else:
                item.distance_km = None  # no map location set: distance unknown

            # Distance filter: skip pharmacies that are too far (or have no location).
            if radius_km is not None and (item.distance_km is None or item.distance_km > radius_km):
                continue
            results.append(item)

        # 3. Sort. Pharmacies with unknown distance always go last.
        def by_distance(item):
            return (item.distance_km is None, item.distance_km or 0, item.price)

        if sort == "price":
            results.sort(key=lambda item: (item.price,) + by_distance(item))
        else:
            results.sort(key=by_distance)

    page_obj = Paginator(results, 20).get_page(request.GET.get("page"))

    # Pins for the map: one per pharmacy on this page (a pharmacy can appear twice,
    # e.g. "Dolo 650" and "Dolo 650 syrup"). Sent to JavaScript with json_script.
    map_pins = {}
    for item in page_obj:
        pharmacy = item.pharmacy
        if pharmacy.has_location and pharmacy.pk not in map_pins:
            map_pins[pharmacy.pk] = {
                "name": pharmacy.name,
                "lat": float(pharmacy.latitude),
                "lng": float(pharmacy.longitude),
                "distance": round(item.distance_km, 1),
                "url": reverse("pharmacy_detail", args=[pharmacy.pk]),
            }

    # Keep the current filters when moving between pages (everything except "page").
    params = request.GET.copy()
    params.pop("page", None)
    # Pass only the location on to the pharmacy detail page, so it can show the distance.
    location_params = QueryDict(mutable=True)
    for key in ("near", "lat", "lng"):
        if request.GET.get(key):
            location_params[key] = request.GET[key]

    return render(request, "medicines/search.html", {
        "form": form,
        "query": query,
        "location": location,
        "page_obj": page_obj,
        "result_count": len(results),
        "map_data": {
            "user": {"lat": location["lat"], "lng": location["lng"], "label": location["label"]},
            "pharmacies": list(map_pins.values()),
        },
        "filter_params": params.urlencode(),
        "location_params": location_params.urlencode(),
        "suggestions": ["Dolo", "Paracetamol", "Pan 40", "Azithromycin", "Insulin"],
    })
