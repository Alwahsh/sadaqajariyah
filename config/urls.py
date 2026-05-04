from django.urls import include, path

from apps.security.views import robots_txt

urlpatterns = [
    path("", include("apps.pages.urls")),
    path("", include("apps.directory.urls")),
    path("accounts/", include("apps.users.urls")),
    path("settings/", include("apps.directory.settings_urls")),
    path("robots.txt", robots_txt, name="robots_txt"),
]

handler404 = "apps.pages.views.handler404"
handler500 = "apps.pages.views.handler500"
