from django.db import connection
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt


def privacy_view(request):
    return render(request, "pages/privacy.html")


def terms_view(request):
    return render(request, "pages/terms.html")


@never_cache
@csrf_exempt
def healthz_view(request):
    """Lightweight liveness/readiness probe.

    - Returns `200 ok` (plain text) when the app is up and the DB connection works.
    - Returns `503 db unavailable` when the DB query raises.
    - No template rendering, no Google Fonts CSS, no auth — minimal overhead so
      Render (or any uptime poller) can hit it on a tight interval.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return HttpResponse("db unavailable", status=503, content_type="text/plain; charset=utf-8")
    return HttpResponse("ok", status=200, content_type="text/plain; charset=utf-8")


def handler404(request, exception=None):
    return render(request, "404.html", status=404)


def handler500(request):
    return render(request, "500.html", status=500)
