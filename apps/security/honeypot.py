"""Honeypot + signed-timestamp anti-bot mixin for unauthenticated POST forms."""
import time

from django import forms
from django.core import signing
from django.core.exceptions import ValidationError

HONEYPOT_FIELD = "nickname_confirm"
TIMESTAMP_FIELD = "form_timestamp"
TIMESTAMP_SALT = "sadaqajariyah.signed_form_timestamp"
TIMESTAMP_MAX_AGE = 86400  # 1 day
TIMESTAMP_MIN_AGE = 2  # 2 seconds

REJECTION_MESSAGE = "Submission could not be processed. Please try again."


def make_timestamp() -> str:
    return signing.dumps(int(time.time()), salt=TIMESTAMP_SALT)


def validate_timestamp(value: str) -> None:
    """Raises ValidationError on too-fast or too-stale submission."""
    try:
        issued = signing.loads(value, salt=TIMESTAMP_SALT, max_age=TIMESTAMP_MAX_AGE)
    except signing.SignatureExpired:
        raise ValidationError(REJECTION_MESSAGE)
    except signing.BadSignature:
        raise ValidationError(REJECTION_MESSAGE)
    except Exception:
        raise ValidationError(REJECTION_MESSAGE)
    elapsed = int(time.time()) - int(issued)
    if elapsed < TIMESTAMP_MIN_AGE:
        raise ValidationError(REJECTION_MESSAGE)
    if elapsed > TIMESTAMP_MAX_AGE:
        raise ValidationError(REJECTION_MESSAGE)


class HoneypotMixin:
    """Mixin for forms. Adds the honeypot field; subclasses opt into the timestamp.

    Subclasses set `enforce_timestamp = True` to require the signed timer.
    """
    enforce_timestamp = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[HONEYPOT_FIELD] = forms.CharField(
            required=False,
            label="Leave this field empty.",
            widget=forms.TextInput(attrs={
                "autocomplete": "off",
                "class": "honeypot",
                "tabindex": "0",
            }),
        )
        if self.enforce_timestamp:
            initial = make_timestamp()
            self.fields[TIMESTAMP_FIELD] = forms.CharField(
                required=True,
                widget=forms.HiddenInput(),
                initial=initial,
            )

    def clean(self):
        cleaned = super().clean()
        # Honeypot — any non-empty value is a rejection.
        value = self.data.get(HONEYPOT_FIELD, "")
        if value and value.strip():
            self.add_error(None, REJECTION_MESSAGE)
        if self.enforce_timestamp:
            ts = self.data.get(TIMESTAMP_FIELD, "")
            try:
                validate_timestamp(ts)
            except ValidationError:
                self.add_error(None, REJECTION_MESSAGE)
        return cleaned
