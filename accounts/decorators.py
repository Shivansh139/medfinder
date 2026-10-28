"""Permission checks that run on the server, before a view is executed."""

from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    """
    Only let users with one of the given roles into a view.

    Usage:
        @role_required(User.Role.PHARMACY)
        def pharmacy_dashboard(request): ...

    - Not logged in   -> sent to the login page (then back here afterwards).
    - Wrong role      -> 403 Forbidden.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
