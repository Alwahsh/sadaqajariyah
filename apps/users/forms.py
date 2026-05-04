import re

from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.security.honeypot import HoneypotMixin

from .reserved import RESERVED_USERNAMES

User = get_user_model()

USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,29}$")
HEX64_RE = re.compile(r"^[a-f0-9]{64}$")


def validate_hex64(value):
    if not HEX64_RE.match(value or ""):
        raise ValidationError(_("Invalid password value."))


class RegistrationForm(HoneypotMixin, forms.Form):
    enforce_timestamp = True

    username = forms.CharField(max_length=30, min_length=3)
    email = forms.EmailField(max_length=254)
    password = forms.CharField(max_length=64, min_length=64)

    def clean_username(self):
        raw = self.cleaned_data["username"].strip()
        if not raw.isascii():
            raise ValidationError(_("Use only ASCII letters, numbers, hyphen, or underscore."))
        normalized = raw.lower()
        if not USERNAME_RE.match(normalized):
            raise ValidationError(_("Username must be 3–30 chars, start with a letter or number, and contain only letters, numbers, hyphen, or underscore."))
        if normalized in RESERVED_USERNAMES:
            raise ValidationError(_("That username is reserved."))
        if User.objects.filter(username__iexact=normalized).exists():
            raise ValidationError(_("That username is already taken."))
        return normalized

    def clean_email(self):
        raw = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=raw).exists():
            raise ValidationError(_("An account with this email already exists."))
        return raw

    def clean_password(self):
        value = self.cleaned_data["password"]
        validate_hex64(value)
        return value

    def save(self):
        user = User(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
            is_active=True,
        )
        user.set_password(self.cleaned_data["password"])
        user.save()
        return user


class EmailLoginForm(HoneypotMixin, forms.Form):
    """Email + client-hashed password login."""

    enforce_timestamp = False

    email = forms.EmailField(max_length=254)
    password = forms.CharField(max_length=64, min_length=64)

    error_messages = {
        "invalid_login": _("Incorrect email or password."),
        "inactive": _("Incorrect email or password."),
    }

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_password(self):
        value = self.cleaned_data["password"]
        if not HEX64_RE.match(value or ""):
            # Don't reveal a password-format error — same generic message.
            raise ValidationError(self.error_messages["invalid_login"])
        return value

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email")
        password = cleaned.get("password")
        if email and password:
            user = authenticate(self.request, email=email, password=password)
            if user is None:
                # Don't reveal "no such email" vs "wrong password" — same message either way.
                # Avoid duplicating with the honeypot-rejection message: skip if the form
                # already has non-field errors from the mixin.
                if not self.non_field_errors():
                    self.add_error(None, self.error_messages["invalid_login"])
            else:
                self.user_cache = user
        return cleaned

    def get_user(self):
        return self.user_cache


class ChangePasswordForm(HoneypotMixin, forms.Form):
    """In-app password change. Both fields are client-hashed before submit."""

    enforce_timestamp = False

    current_password = forms.CharField(max_length=64, min_length=64)
    new_password = forms.CharField(max_length=64, min_length=64)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        value = self.cleaned_data["current_password"]
        if not HEX64_RE.match(value or ""):
            raise ValidationError(_("Incorrect current password."))
        if not self.user.check_password(value):
            raise ValidationError(_("Incorrect current password."))
        return value

    def clean_new_password(self):
        value = self.cleaned_data["new_password"]
        validate_hex64(value)
        return value

    def save(self):
        new_value = self.cleaned_data["new_password"]
        self.user.set_password(new_value)
        self.user.save()
        # Clear must_change_password flag if set.
        try:
            profile = self.user.profile
            if profile.must_change_password:
                profile.must_change_password = False
                profile.save(update_fields=["must_change_password"])
        except Exception:
            pass
        return self.user
