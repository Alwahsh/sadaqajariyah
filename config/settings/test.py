from .base import *  # noqa

DEBUG = False
SECRET_KEY = "test-secret-key-only-for-tests-not-used-anywhere-else-1234567890abcdef"
PEPPER = "test-pepper-only-for-tests-not-used-anywhere-else-1234567890abcdef"

ALLOWED_HOSTS = ["*", "testserver", "localhost"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# In tests we want SITE_IS_PRODUCTION default off so robots.txt non-prod path is exercised by default;
# individual tests will override via override_settings.
SITE_IS_PRODUCTION = False

# Disable password validators since the wire value is a hex hash anyway.
AUTH_PASSWORD_VALIDATORS = []
