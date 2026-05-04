import os

import dj_database_url

from .base import *  # noqa

DEBUG = False

SECRET_KEY = os.environ["SECRET_KEY"]
PEPPER = os.environ["PEPPER"]
assert len(SECRET_KEY) >= 50, "SECRET_KEY must be >= 50 chars in prod"
assert len(PEPPER) >= 32, "PEPPER must be >= 32 chars in prod"

# Production must use Postgres via DATABASE_URL. Fail loud at startup if it's
# missing — without this assertion the app silently falls back to SQLite at
# BASE_DIR/db.sqlite3, which on Render's ephemeral filesystem is wiped on
# every restart, deploy, or sleep cycle.
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
assert DATABASE_URL, (
    "DATABASE_URL is required in production. Without it, Django would write to "
    "an ephemeral SQLite file and lose every profile on the next restart. Link "
    "the Render Postgres database to the web service."
)
assert not DATABASE_URL.startswith("sqlite"), (
    "DATABASE_URL must point at Postgres in production, not SQLite "
    "(SQLite on Render's ephemeral disk loses data on every restart)."
)
DATABASES = {
    "default": dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
        ssl_require=True,
    ),
}

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [h.strip() for h in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if h.strip()]

SITE_IS_PRODUCTION = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "60"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS >= 31536000
SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS >= 31536000

SILENCED_SYSTEM_CHECKS = ["security.W004"]

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
