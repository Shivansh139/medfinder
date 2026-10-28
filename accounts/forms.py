"""Forms for signing up and logging in."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db import transaction

from pharmacies.models import Pharmacy

from .models import User


class BootstrapFormMixin:
    """Adds the right Bootstrap CSS class to every field's input."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = "form-check-input"  # tick box
            elif isinstance(field.widget, forms.Select):
                css_class = "form-select"       # dropdown
            else:
                css_class = "form-control"      # text, number, textarea...
            field.widget.attrs["class"] = css_class


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    """Django's built-in login form, just styled with Bootstrap."""


class CustomerSignUpForm(BootstrapFormMixin, UserCreationForm):
    """Sign-up form for customers. UserCreationForm already checks the two passwords."""

    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.CUSTOMER
        if commit:
            user.save()
        return user


class PharmacySignUpForm(BootstrapFormMixin, UserCreationForm):
    """
    Sign-up form for pharmacies. One form creates two records:
    the User (role = pharmacy) and a Pharmacy (status = pending).
    """

    email = forms.EmailField(required=True)
    pharmacy_name = forms.CharField(max_length=200)
    licence_number = forms.CharField(max_length=50)
    address = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))
    phone = forms.CharField(max_length=20)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_licence_number(self):
        """Give a friendly error if this licence number is already registered."""
        licence = self.cleaned_data["licence_number"].strip()
        if Pharmacy.objects.filter(licence_number__iexact=licence).exists():
            raise forms.ValidationError("A pharmacy with this licence number is already registered.")
        return licence

    @transaction.atomic  # if either save fails, neither record is kept
    def save(self):
        user = super().save(commit=False)
        user.role = User.Role.PHARMACY
        user.save()
        Pharmacy.objects.create(
            owner=user,
            name=self.cleaned_data["pharmacy_name"],
            licence_number=self.cleaned_data["licence_number"],
            address=self.cleaned_data["address"],
            phone=self.cleaned_data["phone"],
            # status is not set here, so it uses the default: PENDING
        )
        return user
