from django.urls import include, path

from apps.pages.views import healthz_view
from apps.security.views import robots_txt

urlpatterns = [
    # Lightweight health probe for Render / uptime checks. Registered both with
    # and without trailing slash so Django's APPEND_SLASH 301 doesn't fire.
    path("healthz", healthz_view, name="healthz"),
    path("healthz/", healthz_view),
    path("", include("apps.pages.urls")),
    path("", include("apps.directory.urls")),
    path("accounts/", include("apps.users.urls")),
    path("settings/", include("apps.directory.settings_urls")),
    path("robots.txt", robots_txt, name="robots_txt"),
]

handler404 = "apps.pages.views.handler404"
handler500 = "apps.pages.views.handler500"
