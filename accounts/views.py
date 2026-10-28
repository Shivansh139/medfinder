"""Views for sign-up and the role-based dashboard redirect."""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import CustomerSignUpForm, PharmacySignUpForm


def signup_choice(request):
    """Let the visitor choose: sign up as a customer or as a pharmacy."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "accounts/signup_choice.html")


def customer_signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = CustomerSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # log the new user in straight away
            messages.success(request, "Welcome to MediFind! Your customer account is ready.")
            return redirect("dashboard")
    else:
        form = CustomerSignUpForm()

    return render(request, "accounts/signup_form.html", {"form": form, "title": "Customer sign up"})


def pharmacy_signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = PharmacySignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration received. An administrator will review your pharmacy.")
            return redirect("dashboard")
    else:
        form = PharmacySignUpForm()

    return render(request, "accounts/signup_form.html", {"form": form, "title": "Pharmacy sign up"})


@login_required
def dashboard(request):
    """One /dashboard/ link for everyone; send each role to its own page."""
    user = request.user
    if user.is_pharmacy:
        return redirect("pharmacy_dashboard")
    if user.is_admin_role or user.is_staff:
        return redirect("admin:index")
    # Customer: show their 5 newest availability requests.
    recent_requests = user.availability_requests.select_related("pharmacy", "medicine")[:5]
    return render(request, "accounts/customer_dashboard.html", {"recent_requests": recent_requests})
