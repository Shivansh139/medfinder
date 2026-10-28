"""
Django settings for the MediFind project.

Secrets and environment-specific values (SECRET_KEY, DEBUG, ALLOWED_HOSTS,
DATABASE_URL) are read from environment variables, never written in code.
Locally they come from a `.env` file (which is NOT committed to git).
On Render they are set in the dashboard.
"""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# BASE_DIR is the project root folder (the one containing manage.py).
BASE_DIR = Path(__file__).resolve().parent.parent

# Load variables from a local .env file if it exists.
# In production there is no .env file; real environment variables are used.
load_dotenv(BASE_DIR / ".env")


# ---------------------------------------------------------------------------
# Core security settings
# ---------------------------------------------------------------------------

# DEBUG shows detailed error pages. It must be False in production,
# so it is only turned on when the environment explicitly says "True".
DEBUG = os.environ.get("DEBUG", "False") == "True"

# SECRET_KEY signs sessions and CSRF tokens. It must be kept private.
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "SECRET_KEY is not set. Copy .env.example to .env and fill it in."
    )

# Which domain names this site may be served under, e.g. "localhost,127.0.0.1".
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

# Sites allowed to send forms (POST) to us over HTTPS. Django checks this as
# part of CSRF protection.
CSRF_TRUSTED_ORIGINS = []

# Render sets RENDER_EXTERNAL_HOSTNAME to the site's public address
# (e.g. "medifind-xxxx.onrender.com"), so we never have to type it by hand.
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")

# HTTPS-only settings for production. They are off while DEBUG is on, because
# the local development server only speaks plain http.
if not DEBUG:
    # Render handles HTTPS and forwards the request to Django as plain http,
    # adding the header "X-Forwarded-Proto: https". Trust it, so Django knows
    # the visitor really used HTTPS.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    # Send any http:// visitor to https://. The health check is exempt so
    # Render's internal check gets a direct answer.
    SECURE_SSL_REDIRECT = True
    SECURE_REDIRECT_EXEMPT = [r"^healthz/$"]
    # Only send the login (session) and CSRF cookies over HTTPS.
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # HSTS: tell browsers to use only HTTPS for this site for the next hour.
    # Kept short on purpose; browsers remember it and it cannot be undone early.
    SECURE_HSTS_SECONDS = 3600


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    # Django's built-in apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    # Serve static files through WhiteNoise in development too (same as
    # production). With DEBUG on it tells the browser not to reuse stale
    # copies of our CSS/JS. Must come before django.contrib.staticfiles.
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    # Our own apps
    "core",
    "accounts",
    "pharmacies",
    "medicines",
    "availability",
]

# Use our own User model (accounts/models.py) instead of Django's default.
AUTH_USER_MODEL = "accounts.User"

# Where @login_required sends visitors who are not logged in.
LOGIN_URL = "login"
# After logging in, go to the dashboard (which redirects by role).
LOGIN_REDIRECT_URL = "dashboard"
# After logging out, go back to the home page.
LOGOUT_REDIRECT_URL = "home"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise serves CSS/JS/images efficiently in production.
    # It must come directly after SecurityMiddleware.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "medifind.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Project-wide templates (like base.html) live in /templates.
        "DIRS": [BASE_DIR / "templates"],
        # Each app can also have its own templates/ folder.
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "medifind.wsgi.application"


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# If DATABASE_URL is set (e.g. a Neon PostgreSQL URL in production), use it.
# Otherwise fall back to a simple SQLite file for local development.

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,  # reuse connections for up to 10 minutes
            # Neon's free database sleeps when idle, which closes old
            # connections. Check a reused connection before using it.
            conn_health_checks=True,
            ssl_require=True,  # Neon requires encrypted connections
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# ---------------------------------------------------------------------------
# Password validation (Django built-in rules)
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ---------------------------------------------------------------------------
# Language and time
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True  # store times in UTC in the database, show them in TIME_ZONE


# ---------------------------------------------------------------------------
# Static files (CSS, JavaScript, images)
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
# Our own static files during development.
STATICFILES_DIRS = [BASE_DIR / "static"]
# `collectstatic` copies all static files here for WhiteNoise to serve.
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # In production: compress files and add a content hash to filenames
    # (cache-friendly). This needs `collectstatic` to have been run, so during
    # local development we use Django's plain storage instead.
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
# With DEBUG off, Django does not show error details on the page. Print them
# to the console instead, so they appear in Render's "Logs" tab.

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}
