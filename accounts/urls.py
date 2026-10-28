"""URL patterns for accounts (all start with /accounts/)."""

from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import LoginForm

urlpatterns = [
    path("signup/", views.signup_choice, name="signup"),
    path("signup/customer/", views.customer_signup, name="customer_signup"),
    path("signup/pharmacy/", views.pharmacy_signup, name="pharmacy_signup"),
    # Django's built-in login/logout views; we only supply the template and form.
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=LoginForm,
            redirect_authenticated_user=True,  # logged-in users skip the login page
        ),
        name="login",
    ),
    # LogoutView only accepts POST (a form button), which protects against CSRF.
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
