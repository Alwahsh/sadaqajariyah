from django.conf import settings
from django.shortcuts import redirect

CSP_VALUE = (
    "default-src 'self'; "
    "img-src 'self' data:; "
    "style-src 'self' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "script-src 'self'; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "form-action 'self'; "
    "base-uri 'self';"
)


class CSPMiddleware:
    """Set Content-Security-Policy on every response unless one is already set."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if "Content-Security-Policy" not in response.headers:
            response.headers["Content-Security-Policy"] = CSP_VALUE
        return response


class NoIndexHeaderMiddleware:
    """Add X-Robots-Tag: noindex,nofollow on every response when SITE_IS_PRODUCTION is False."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not getattr(settings, "SITE_IS_PRODUCTION", False):
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
        return response


# Endpoints exempt from must-change-password redirect:
# - the change-password page itself
# - logout
# - static/media
ALLOWED_PATHS_WHEN_FORCED_PWCHANGE = (
    "/settings/password/",
    "/accounts/logout/",
    "/healthz",
)


class MustChangePasswordMiddleware:
    """When a user has Profile.must_change_password=True, redirect every authenticated
    request other than the change-password page or logout to /settings/password/."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            try:
                must = user.profile.must_change_password
            except Exception:
                must = False
            if must:
                path = request.path
                if not any(path == p or path.startswith(p) for p in ALLOWED_PATHS_WHEN_FORCED_PWCHANGE):
                    if not path.startswith(settings.STATIC_URL):
                        return redirect("/settings/password/")
        return self.get_response(request)
