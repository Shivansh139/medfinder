"""URL patterns for pharmacy inventory (all start with /pharmacy/inventory/)."""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.inventory_list, name="inventory_list"),
    path("add/", views.inventory_add, name="inventory_add"),
    # <int:pk> captures the item's id from the URL, e.g. /pharmacy/inventory/7/edit/
    path("<int:pk>/edit/", views.inventory_edit, name="inventory_edit"),
    path("<int:pk>/delete/", views.inventory_delete, name="inventory_delete"),
]
