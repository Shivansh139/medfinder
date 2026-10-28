"""Forms for availability requests."""

from django import forms

from accounts.forms import BootstrapFormMixin

from .models import AvailabilityRequest


class RequestForm(BootstrapFormMixin, forms.ModelForm):
    """What the customer fills in. Customer, pharmacy and medicine are set by the view."""

    class Meta:
        model = AvailabilityRequest
        fields = ("quantity", "note", "contact_phone")
        labels = {
            "quantity": "How many do you need?",
            "note": "Message to the pharmacy (optional)",
            "contact_phone": "Your phone number (optional)",
        }
        help_texts = {
            "note": "e.g. Need it by this evening.",
            "contact_phone": "Only this pharmacy will see it, so they can call you back.",
        }
        widgets = {"note": forms.Textarea(attrs={"rows": 2})}


class RespondForm(BootstrapFormMixin, forms.ModelForm):
    """What the pharmacy fills in to answer a request."""

    # Only these two answers are allowed. Anything else (e.g. a tampered
    # "cancelled") fails validation as "Select a valid choice".
    status = forms.ChoiceField(
        label="Your answer",
        choices=[
            (AvailabilityRequest.Status.CONFIRMED, "Confirmed – we have it"),
            (AvailabilityRequest.Status.UNAVAILABLE, "Unavailable – we don't have it"),
        ],
    )

    class Meta:
        model = AvailabilityRequest
        fields = ("status", "pharmacy_reply")
        labels = {"pharmacy_reply": "Reply to the customer (optional)"}
        help_texts = {"pharmacy_reply": "e.g. Available, ₹32 per strip, open till 10 pm."}
        widgets = {"pharmacy_reply": forms.Textarea(attrs={"rows": 2})}
