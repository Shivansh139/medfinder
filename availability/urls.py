"""URL patterns for availability requests."""

from django.urls import path

from . import views

urlpatterns = [
    # Customers
    path("requests/", views.my_requests, name="my_requests"),
    path("requests/new/<int:item_pk>/", views.request_create, name="request_create"),
    path("requests/<int:pk>/cancel/", views.request_cancel, name="request_cancel"),
    # Pharmacies
    path("pharmacy/requests/", views.pharmacy_requests, name="pharmacy_requests"),
    path("pharmacy/requests/<int:pk>/respond/", views.request_respond, name="request_respond"),
]
