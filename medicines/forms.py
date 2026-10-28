"""Forms for a pharmacy's inventory."""

from django import forms

from accounts.forms import BootstrapFormMixin
from pharmacies.forms import LocationForm

from .models import InventoryItem, Medicine


class SearchForm(BootstrapFormMixin, LocationForm):
    """
    The customer search box and filters. Values come from the URL (GET),
    so a search can be bookmarked or shared. Every field is optional and
    validated on the server; a tampered value falls back to its default.
    """

    q = forms.CharField(
        required=False, max_length=100, label="Medicine",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Dolo 650 or paracetamol"}),
    )
    # The first choice of each list is the default.
    availability = forms.ChoiceField(
        required=False,
        choices=[("in_stock", "In stock only"), ("all", "All")],
    )
    radius = forms.ChoiceField(
        required=False,
        label="Distance",
        choices=[("", "Any distance"), ("2", "Within 2 km"), ("5", "Within 5 km"),
                 ("10", "Within 10 km"), ("20", "Within 20 km")],
    )
    sort = forms.ChoiceField(
        required=False,
        label="Sort by",
        choices=[("distance", "Nearest first"), ("price", "Lowest price")],
    )

    # Show the search box first, then the filters, then the location fields.
    field_order = ["q", "availability", "radius", "sort", "near", "lat", "lng"]


class InventoryAddForm(BootstrapFormMixin, forms.ModelForm):
    """Add a catalogue medicine to the pharmacy's stock."""

    class Meta:
        model = InventoryItem
        fields = ("medicine", "quantity", "price")
        labels = {"price": "Price (₹)"}
        help_texts = {"quantity": "Enter 0 if it is currently out of stock."}

    def __init__(self, *args, pharmacy, **kwargs):
        super().__init__(*args, **kwargs)
        # Only offer medicines this pharmacy does not stock yet.
        # A tampered request with an already-stocked medicine is then rejected
        # as "Select a valid choice", so no duplicate row can be created.
        already_stocked = pharmacy.inventory.values_list("medicine_id", flat=True)
        self.fields["medicine"].queryset = Medicine.objects.exclude(id__in=already_stocked)


class InventoryEditForm(BootstrapFormMixin, forms.ModelForm):
    """Change quantity and price. The medicine itself cannot be changed."""

    class Meta:
        model = InventoryItem
        fields = ("quantity", "price")
        labels = {"price": "Price (₹)"}
        help_texts = {"quantity": "Set to 0 when it runs out; customers will see it as unavailable."}
