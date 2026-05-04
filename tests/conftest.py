"""Shared fixtures and helpers for the spec test suite."""
import time

import pytest
from django.contrib.auth import get_user_model
from django.core import signing

from apps.security.honeypot import HONEYPOT_FIELD, TIMESTAMP_FIELD, TIMESTAMP_SALT
from apps.users.client_hash import derive_client_hash


User = get_user_model()


def hex_hash(plaintext: str, email: str) -> str:
    return derive_client_hash(plaintext, email)


def make_signed_timestamp(offset_seconds: int = -10) -> str:
    """Return a signed timestamp the form will accept (default 10s ago)."""
    return signing.dumps(int(time.time()) + offset_seconds, salt=TIMESTAMP_SALT)


@pytest.fixture
def signup_post_payload():
    """Build a registration POST that satisfies all form-level guards."""
    def _build(username="alice", email="alice@example.com", plaintext="alice-pw-1234",
               *, ts_offset=-10, honeypot="", extra=None):
        data = {
            "username": username,
            "email": email,
            "password": hex_hash(plaintext, email),
            HONEYPOT_FIELD: honeypot,
            TIMESTAMP_FIELD: make_signed_timestamp(ts_offset),
        }
        if extra:
            data.update(extra)
        return data
    return _build


@pytest.fixture
def make_user(db):
    """Create a user via the registration code path (form-equivalent)."""
    def _make(username="alice", email="alice@example.com", plaintext="alice-pw-1234",
              is_active=True):
        user = User(username=username, email=email, is_active=is_active)
        user.set_password(hex_hash(plaintext, email))
        user.save()
        return user
    return _make


@pytest.fixture
def make_profile_with_scheduling(make_user):
    """Create a user + populated profile suitable for the directory."""
    def _make(username="alice", email="alice@example.com", plaintext="alice-pw-1234",
              first_name="Alice", last_name="Anderson",
              bio="A community member offering thoughtful conversation and mentoring.",
              scheduling_url="https://calendly.com/alice/30min",
              feedback_url="",
              is_verified=False, is_active=True):
        user = make_user(username=username, email=email, plaintext=plaintext, is_active=is_active)
        profile = user.profile
        profile.first_name = first_name
        profile.last_name = last_name
        profile.bio = bio
        profile.scheduling_url = scheduling_url
        profile.feedback_url = feedback_url
        profile.is_verified = is_verified
        profile.save()
        return profile
    return _make


@pytest.fixture
def login_client(client, make_user):
    """Helper to log in via real /accounts/login/ POST flow (client-hashed)."""
    def _login(email="alice@example.com", plaintext="alice-pw-1234"):
        from apps.security.honeypot import HONEYPOT_FIELD
        resp = client.post("/accounts/login/", {
            "email": email,
            "password": hex_hash(plaintext, email),
            HONEYPOT_FIELD: "",
        })
        return resp
    return _login
