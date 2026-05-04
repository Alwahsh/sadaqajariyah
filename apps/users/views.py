from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from .forms import ChangePasswordForm, EmailLoginForm, RegistrationForm


@csrf_protect
@never_cache
@require_http_methods(["GET", "POST"])
def signup_view(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user, backend="apps.users.backends.EmailAuthBackend")
            return redirect(settings.LOGIN_REDIRECT_URL)
    else:
        form = RegistrationForm()
    return render(request, "users/signup.html", {"form": form})


@csrf_protect
@never_cache
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)
    next_url = request.GET.get("next") or request.POST.get("next") or ""
    if request.method == "POST":
        form = EmailLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user, backend="apps.users.backends.EmailAuthBackend")
            target = next_url if next_url and next_url.startswith("/") else settings.LOGIN_REDIRECT_URL
            return redirect(target)
    else:
        form = EmailLoginForm(request)
    return render(request, "users/login.html", {"form": form, "next": next_url})


@require_http_methods(["GET", "POST"])
def logout_view(request):
    auth_logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)


@login_required
@csrf_protect
@never_cache
@require_http_methods(["GET", "POST"])
def change_password_view(request):
    if request.method == "POST":
        form = ChangePasswordForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, "Password changed.")
            return redirect("/settings/")
    else:
        form = ChangePasswordForm(request.user)
    return render(request, "users/change_password.html", {"form": form})
