"""Base settings shared by dev/prod/test."""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

sys.path.insert(0, str(BASE_DIR / "apps"))

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-not-for-production-do-not-use-in-real-deployment-xxxxxxxxxxxxxxx")
PEPPER = os.environ.get("PEPPER", "dev-pepper-not-for-production-please-replace-with-random-value-xxxxxxxxxx")

DEBUG = False
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "crispy_forms",
    "crispy_tailwind",
    "apps.users",
    "apps.directory",
    "apps.security",
    "apps.pages",
]

MIDDLEWARE = [
    # MUST be first — short-circuits /healthz before the host check (Render's
    # probe sends the platform-internal hostname, which isn't in ALLOWED_HOSTS).
    "apps.security.middleware.HealthCheckMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.security.middleware.NoIndexHeaderMiddleware",
    "apps.security.middleware.MustChangePasswordMiddleware",
    "apps.security.middleware.CSPMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.pages.context_processors.site_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 1}},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Auth: email-based login, peppered hasher.
AUTHENTICATION_BACKENDS = ["apps.users.backends.EmailAuthBackend"]
PASSWORD_HASHERS = ["apps.users.hashers.PepperedPBKDF2Hasher"]

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/settings/"
LOGOUT_REDIRECT_URL = "/"

# Email: locmem everywhere — v1 sends zero outbound mail.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Crispy / Tailwind.
CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

# Site flags.
SITE_IS_PRODUCTION = os.environ.get("SITE_IS_PRODUCTION") == "1"
OPERATOR_CONTACT_EMAIL = os.environ.get("OPERATOR_CONTACT_EMAIL", "operator@sadaqajariyah.online")
CANONICAL_HOST = os.environ.get("CANONICAL_HOST", "sadaqajariyah.online")

# Security defaults.
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False

# Scheduling host allowlist.
KNOWN_SCHEDULING_HOSTS = [
    "calendly.com",
    "cal.com",
    "savvycal.com",
    "calendar.google.com",
    "calendar.app.google",
    "koalendar.com",
    "tidycal.com",
    "youcanbook.me",
    "zcal.co",
]

# Hashing parameters (must be byte-for-byte equal to apps/users/static/users/auth-hash.js).
CLIENT_HASH_ITERATIONS = 100_000
CLIENT_HASH_DKLEN = 32
