"""Forms for pharmacy users."""

from django import forms

from accounts.forms import BootstrapFormMixin

from .models import Pharmacy
from .utils import PRESET_LOCATIONS


class LocationForm(forms.Form):
    """
    Where the customer is, read from the URL (?near=... or ?lat=...&lng=...).
    Used by the search page and the pharmacy detail page.
    All fields are optional: invalid values are simply ignored (see resolve_location).
    """

    near = forms.ChoiceField(
        required=False,
        label="Near",
        choices=[(key, label) for key, (label, _lat, _lng) in PRESET_LOCATIONS.items()],
    )
    # Filled in by the "Use my location" button; hidden from the user.
    lat = forms.FloatField(required=False, min_value=-90, max_value=90, widget=forms.HiddenInput)
    lng = forms.FloatField(required=False, min_value=-180, max_value=180, widget=forms.HiddenInput)


class PharmacyProfileForm(BootstrapFormMixin, forms.ModelForm):
    """
    Lets a pharmacy edit its own profile.

    licence_number and status are deliberately NOT listed in `fields`:
    a ModelForm ignores any field that is not listed, so even a tampered
    request cannot change them.
    """

    class Meta:
        model = Pharmacy
        fields = (
            "name", "address", "phone", "opening_hours",
            "home_delivery_available", "home_delivery_phone",
            "latitude", "longitude",
        )
        labels = {
            "name": "Pharmacy name",
            "home_delivery_available": "We offer home delivery",
        }
        help_texts = {
            "opening_hours": "Optional, e.g. 9 am – 9 pm, closed Sunday.",
            "home_delivery_phone": "Required if you offer home delivery.",
            "latitude": "Click the map to fill this in.",
            "longitude": "Click the map to fill this in.",
        }
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            # step="any" lets the browser accept decimals like 12.971599
            "latitude": forms.NumberInput(attrs={"step": "any"}),
            "longitude": forms.NumberInput(attrs={"step": "any"}),
        }

    def clean(self):
        """Latitude and longitude must be given together, or both left empty."""
        cleaned = super().clean()
        lat = cleaned.get("latitude")
        lng = cleaned.get("longitude")
        if (lat is None) != (lng is None):
            raise forms.ValidationError("Set both latitude and longitude, or leave both empty.")

        # Home delivery needs a phone number customers can call.
        if cleaned.get("home_delivery_available"):
            if not cleaned.get("home_delivery_phone", "").strip():
                self.add_error("home_delivery_phone", "Enter a delivery phone number, or untick home delivery.")
        else:
            # No delivery: do not keep an old, unused delivery number.
            cleaned["home_delivery_phone"] = ""
        return cleaned
