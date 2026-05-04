"""Spec §2 (registration) and §3 (login) flows."""
import pytest
from django.contrib.auth import SESSION_KEY, get_user_model
from django.core import mail

from apps.users.client_hash import derive_client_hash

User = get_user_model()


@pytest.mark.django_db
def test_successful_registration_logs_in_and_redirects(client, signup_post_payload):
    resp = client.post("/accounts/signup/", signup_post_payload())
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/settings/"
    assert SESSION_KEY in client.session
    user = User.objects.get(email="alice@example.com")
    profile = user.profile
    assert profile.is_verified is False
    assert profile.must_change_password is False
    assert profile.bio == ""
    assert profile.scheduling_url == ""
    assert profile.feedback_url == ""


@pytest.mark.django_db
def test_registration_rejects_plaintext_password(client, signup_post_payload):
    """Submitting a non-hex value for password should fail (server-side hex64 check)."""
    payload = signup_post_payload()
    payload["password"] = "plaintext-too-short"
    resp = client.post("/accounts/signup/", payload)
    assert resp.status_code == 200
    assert User.objects.filter(email="alice@example.com").count() == 0


@pytest.mark.django_db
def test_no_email_after_registration(client, signup_post_payload):
    mail.outbox.clear()
    resp = client.post("/accounts/signup/", signup_post_payload())
    assert resp.status_code == 302
    assert mail.outbox == []


@pytest.mark.django_db
def test_login_case_insensitive_on_email(client, make_user):
    make_user(email="alice@example.com", plaintext="alice-pw-1234")
    from apps.security.honeypot import HONEYPOT_FIELD
    resp = client.post("/accounts/login/", {
        "email": "ALICE@example.com",
        "password": derive_client_hash("alice-pw-1234", "alice@example.com"),
        HONEYPOT_FIELD: "",
    })
    assert resp.status_code == 302
    assert SESSION_KEY in client.session


@pytest.mark.django_db
def test_logout_clears_session(client, make_user, login_client):
    make_user()
    login_client()
    assert SESSION_KEY in client.session
    resp = client.post("/accounts/logout/")
    assert resp.status_code == 302
    assert SESSION_KEY not in client.session


@pytest.mark.django_db
def test_no_email_in_any_normal_flow(client, signup_post_payload, make_user, login_client):
    mail.outbox.clear()
    # Registration
    client.post("/accounts/signup/", signup_post_payload(username="alice", email="alice@example.com"))
    # Logout
    client.post("/accounts/logout/")
    # Login again
    login_client()
    # Profile save (empty form is rejected, but still no email)
    client.post("/settings/", {
        "first_name": "Alice", "last_name": "",
        "bio": "A community member offering thoughtful conversation.",
        "scheduling_url": "", "feedback_url": "",
        "providerservice_set-TOTAL_FORMS": "0",
        "providerservice_set-INITIAL_FORMS": "0",
        "providerservice_set-MIN_NUM_FORMS": "0",
        "providerservice_set-MAX_NUM_FORMS": "12",
    })
    assert mail.outbox == []


@pytest.mark.django_db
def test_no_password_reset_url(client):
    """Spec §13 — no /accounts/password_reset/ URLs are mounted."""
    for path in [
        "/accounts/password_reset/",
        "/accounts/password_reset/done/",
        "/accounts/reset/abc/abc/",
        "/accounts/reset/done/",
    ]:
        resp = client.get(path)
        assert resp.status_code == 404, path


@pytest.mark.django_db
def test_login_invalid_credentials_generic_error(client, make_user):
    make_user(plaintext="alice-pw-1234")
    from apps.security.honeypot import HONEYPOT_FIELD
    # Wrong password
    resp = client.post("/accounts/login/", {
        "email": "alice@example.com",
        "password": derive_client_hash("nope", "alice@example.com"),
        HONEYPOT_FIELD: "",
    })
    assert resp.status_code == 200
    assert SESSION_KEY not in client.session
    # The error doesn't reveal whether the email exists vs whether the password is wrong:
    body = resp.content.decode().lower()
    assert "incorrect" in body or "invalid" in body


@pytest.mark.django_db
def test_login_can_submit_quickly_no_timer(client, make_user):
    """Spec: login is NOT timer-protected (only registration is)."""
    make_user(plaintext="alice-pw-1234")
    # Don't include any timestamp — login form doesn't use one.
    from apps.security.honeypot import HONEYPOT_FIELD
    resp = client.post("/accounts/login/", {
        "email": "alice@example.com",
        "password": derive_client_hash("alice-pw-1234", "alice@example.com"),
        HONEYPOT_FIELD: "",
    })
    assert resp.status_code == 302
