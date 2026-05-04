"""Spec §2.5 — honeypot + signed-timestamp on registration; honeypot only on login."""
import time

import pytest
from django.contrib.auth import SESSION_KEY, get_user_model

from apps.security.honeypot import (HONEYPOT_FIELD, REJECTION_MESSAGE,
                                    TIMESTAMP_FIELD, TIMESTAMP_SALT)
from apps.users.client_hash import derive_client_hash

User = get_user_model()


@pytest.mark.django_db
def test_registration_rejects_honeypot_filled(client, signup_post_payload):
    payload = signup_post_payload(honeypot="bot-payload")
    resp = client.post("/accounts/signup/", payload)
    assert resp.status_code == 200
    assert User.objects.filter(email="alice@example.com").count() == 0
    assert REJECTION_MESSAGE in resp.content.decode()


@pytest.mark.django_db
def test_registration_rejects_too_fast(client, signup_post_payload):
    """Submission with timestamp < 2s ago is rejected."""
    payload = signup_post_payload(ts_offset=0)  # issued just now
    resp = client.post("/accounts/signup/", payload)
    assert resp.status_code == 200
    assert User.objects.filter(email="alice@example.com").count() == 0


@pytest.mark.django_db
def test_registration_rejects_stale_timestamp(client, signup_post_payload):
    """Submission with timestamp > 1 day ago is rejected."""
    # The signed value was issued well outside the SignatureExpired window.
    payload = signup_post_payload(ts_offset=-86_500)  # ~1 day + 100s ago
    resp = client.post("/accounts/signup/", payload)
    assert resp.status_code == 200
    assert User.objects.filter(email="alice@example.com").count() == 0


@pytest.mark.django_db
def test_login_rejects_honeypot_filled(client, make_user):
    make_user(plaintext="alice-pw-1234")
    resp = client.post("/accounts/login/", {
        "email": "alice@example.com",
        "password": derive_client_hash("alice-pw-1234", "alice@example.com"),
        HONEYPOT_FIELD: "bot-payload",
    })
    assert resp.status_code == 200
    assert SESSION_KEY not in client.session
    assert REJECTION_MESSAGE in resp.content.decode()


@pytest.mark.django_db
def test_honeypot_field_present_in_signup_form(client):
    resp = client.get("/accounts/signup/")
    body = resp.content.decode()
    assert f'name="{HONEYPOT_FIELD}"' in body
    assert "Leave this field empty" in body
    # Honeypot must NOT have aria-hidden or tabindex=-1 (per spec §14).
    # Look for the honeypot input element specifically.
    assert 'aria-hidden="true"' not in _excerpt_around(body, "nickname_confirm")
    assert 'tabindex="-1"' not in _excerpt_around(body, "nickname_confirm")


def _excerpt_around(haystack: str, needle: str, span: int = 200) -> str:
    idx = haystack.find(needle)
    if idx < 0:
        return ""
    start = max(0, idx - span)
    end = min(len(haystack), idx + span)
    return haystack[start:end]
