"""Views (page handlers) for the core app."""

from django.db import DatabaseError, connection
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe


def home(request):
    """Show the public home page. Anyone can view it."""
    return render(request, "core/home.html")


@require_safe  # GET or HEAD only
@never_cache  # always check live, never answer from a cache
def health_check(request):
    """
    Used by Render to check the site is alive. It runs the smallest possible
    database query, so it also shows whether the database can be reached.
    Answers "ok" (200), or "database unavailable" (503). Shows no other data.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return HttpResponse("database unavailable", status=503, content_type="text/plain")
    return HttpResponse("ok", content_type="text/plain")
