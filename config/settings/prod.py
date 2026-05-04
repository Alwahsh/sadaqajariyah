import os
from .base import *  # noqa

DEBUG = False

SECRET_KEY = os.environ["SECRET_KEY"]
PEPPER = os.environ["PEPPER"]
assert len(SECRET_KEY) >= 50, "SECRET_KEY must be >= 50 chars in prod"
assert len(PEPPER) >= 32, "PEPPER must be >= 32 chars in prod"

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
