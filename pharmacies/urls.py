"""URL patterns for pharmacy users (all start with /pharmacy/)."""

from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/", views.pharmacy_dashboard, name="pharmacy_dashboard"),
    path("profile/", views.pharmacy_profile, name="pharmacy_profile"),
]
