from django.conf import settings


def site_settings(request):
    return {
        "OPERATOR_CONTACT_EMAIL": getattr(settings, "OPERATOR_CONTACT_EMAIL", ""),
        "SITE_IS_PRODUCTION": getattr(settings, "SITE_IS_PRODUCTION", False),
    }
