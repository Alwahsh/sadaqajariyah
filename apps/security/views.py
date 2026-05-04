from django.conf import settings
from django.http import HttpResponse


PROD_ROBOTS = (
    "User-agent: *\n"
    "Allow: /\n"
    "Allow: /p/\n"
    "Disallow: /accounts/\n"
    "Disallow: /settings/\n"
)

NONPROD_ROBOTS = (
    "User-agent: *\n"
    "Disallow: /\n"
)


def robots_txt(request):
    body = PROD_ROBOTS if getattr(settings, "SITE_IS_PRODUCTION", False) else NONPROD_ROBOTS
    response = HttpResponse(body, content_type="text/plain")
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response
