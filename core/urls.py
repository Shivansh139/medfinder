"""URL patterns for the core app."""

from django.urls import path

from . import views

urlpatterns = [
    # name="home" lets templates link to it with {% url 'home' %}.
    path("", views.home, name="home"),
    # Health check for Render (see views.health_check).
    path("healthz/", views.health_check, name="health_check"),
]
