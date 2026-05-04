from django.shortcuts import render


def privacy_view(request):
    return render(request, "pages/privacy.html")


def terms_view(request):
    return render(request, "pages/terms.html")


def handler404(request, exception=None):
    return render(request, "404.html", status=404)


def handler500(request):
    return render(request, "500.html", status=500)
