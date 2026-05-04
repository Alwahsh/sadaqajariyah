"""Spec §2.4, §3, §9 — client-side hashing parity + peppered hasher."""
import pytest
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model

from apps.users.client_hash import derive_client_hash
from apps.users.hashers import PepperedPBKDF2Hasher
from tests.conftest import hex_hash

User = get_user_model()


@pytest.mark.django_db
def test_peppered_hasher_round_trip(make_user):
    user = make_user(plaintext="alice-pw-1234")
    client_hash = hex_hash("alice-pw-1234", "alice@example.com")
    assert user.check_password(client_hash) is True


@pytest.mark.django_db
def test_peppered_hasher_rejects_mismatch(make_user):
    user = make_user(plaintext="alice-pw-1234")
    assert user.check_password("wrong") is False


@pytest.mark.django_db
def test_changing_pepper_invalidates_existing_hash(make_user, settings):
    user = make_user(plaintext="alice-pw-1234")
    client_hash = hex_hash("alice-pw-1234", "alice@example.com")
    assert user.check_password(client_hash) is True
    settings.PEPPER = "different-pepper-value-still-32-chars-or-more"
    assert user.check_password(client_hash) is False


@pytest.mark.django_db
def test_registration_post_login_round_trip(client, signup_post_payload):
    """Sign up via the registration form, then log in via the login form,
    to prove client-side hashing parity end-to-end."""
    resp = client.post("/accounts/signup/", signup_post_payload(
        username="alice", email="alice@example.com", plaintext="my-real-password"))
    assert resp.status_code == 302
    client.logout()
    # Log in via the email login form using the client-derived hash.
    from apps.security.honeypot import HONEYPOT_FIELD
    resp2 = client.post("/accounts/login/", {
        "email": "ALICE@example.com",  # mixed case
        "password": derive_client_hash("my-real-password", "alice@example.com"),
        HONEYPOT_FIELD: "",
    })
    assert resp2.status_code == 302


@pytest.mark.django_db
def test_login_rejects_plaintext_password(client, make_user):
    """Submitting a plaintext value (length != 64 hex chars) should fail."""
    make_user(plaintext="alice-pw-1234")
    from apps.security.honeypot import HONEYPOT_FIELD
    resp = client.post("/accounts/login/", {
        "email": "alice@example.com",
        "password": "alice-pw-1234",  # plaintext, not a hash
        HONEYPOT_FIELD: "",
    })
    assert resp.status_code == 200  # form re-rendered, no session
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_login_by_username_does_not_work(client, make_user):
    make_user(username="alice", email="alice@example.com", plaintext="alice-pw-1234")
    from apps.security.honeypot import HONEYPOT_FIELD
    resp = client.post("/accounts/login/", {
        "username": "alice",  # Wrong key
        "password": derive_client_hash("alice-pw-1234", "alice@example.com"),
        HONEYPOT_FIELD: "",
    })
    assert resp.status_code == 200
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_login_inactive_user_is_rejected(client, make_user):
    make_user(plaintext="alice-pw-1234", is_active=False)
    from apps.security.honeypot import HONEYPOT_FIELD
    resp = client.post("/accounts/login/", {
        "email": "alice@example.com",
        "password": derive_client_hash("alice-pw-1234", "alice@example.com"),
        HONEYPOT_FIELD: "",
    })
    assert resp.status_code == 200
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_authenticate_returns_none_for_unknown_email():
    from apps.users.backends import EmailAuthBackend
    backend = EmailAuthBackend()
    assert backend.authenticate(None, email="nobody@example.com", password="abc") is None


def test_hasher_algorithm_string():
    h = PepperedPBKDF2Hasher()
    assert h.algorithm == "peppered_pbkdf2_sha256"
    # Encode round-trip with a known salt.
    encoded = h.encode("hello", "salty")
    assert h.verify("hello", encoded) is True
    assert h.verify("HELLO", encoded) is False
