"""
Top-level URL configuration for MediFind.

Each app keeps its own urls.py; here we just plug them in.
"""

from django.contrib import admin
from django.urls import include, path

from accounts import views as account_views
from medicines import views as medicine_views
from pharmacies import views as pharmacy_views

urlpatterns = [
    # Django's built-in admin site (for administrators).
    path("admin/", admin.site.urls),
    # Sign up, login, logout.
    path("accounts/", include("accounts.urls")),
    # One dashboard link for everyone; it redirects by role.
    path("dashboard/", account_views.dashboard, name="dashboard"),
    # Public pages: medicine search and pharmacy details (no login needed).
    path("search/", medicine_views.search, name="search"),
    path("pharmacies/<int:pk>/", pharmacy_views.pharmacy_detail, name="pharmacy_detail"),
    # Availability requests: /requests/... (customers) and /pharmacy/requests/... (pharmacies).
    path("", include("availability.urls")),
    # Pages for pharmacy users. The inventory URLs come first because they are
    # more specific than "pharmacy/".
    path("pharmacy/inventory/", include("medicines.urls")),
    path("pharmacy/", include("pharmacies.urls")),
    # Everything else is handled by the core app.
    path("", include("core.urls")),
]
