"""Spec §6 — in-app password change."""
import pytest
from django.contrib.auth import SESSION_KEY
from django.core import mail

from apps.users.client_hash import derive_client_hash


@pytest.mark.django_db
def test_anon_redirects_to_login(client):
    resp = client.get("/settings/password/")
    assert resp.status_code == 302
    assert "/accounts/login/" in resp.headers["Location"]


@pytest.mark.django_db
def test_change_password_success(client, make_user, login_client):
    make_user(plaintext="alice-pw-1234")
    login_client()
    new_hash = derive_client_hash("new-pw", "alice@example.com")
    cur_hash = derive_client_hash("alice-pw-1234", "alice@example.com")
    from apps.security.honeypot import HONEYPOT_FIELD
    resp = client.post("/settings/password/", {
        "current_password": cur_hash,
        "new_password": new_hash,
        HONEYPOT_FIELD: "",
    })
    assert resp.status_code == 302
    # Session preserved (update_session_auth_hash).
    assert SESSION_KEY in client.session
    # Re-login with new password works.
    client.logout()
    resp = client.post("/accounts/login/", {
        "email": "alice@example.com",
        "password": new_hash,
        HONEYPOT_FIELD: "",
    })
    assert resp.status_code == 302


@pytest.mark.django_db
def test_change_password_wrong_current(client, make_user, login_client):
    make_user(plaintext="alice-pw-1234")
    login_client()
    from apps.security.honeypot import HONEYPOT_FIELD
    resp = client.post("/settings/password/", {
        "current_password": derive_client_hash("WRONG", "alice@example.com"),
        "new_password": derive_client_hash("new-pw", "alice@example.com"),
        HONEYPOT_FIELD: "",
    })
    assert resp.status_code == 200


@pytest.mark.django_db
def test_change_password_clears_must_change_flag(client, make_user, login_client):
    user = make_user(plaintext="alice-pw-1234")
    user.profile.must_change_password = True
    user.profile.save()
    login_client()
    from apps.security.honeypot import HONEYPOT_FIELD
    resp = client.post("/settings/password/", {
        "current_password": derive_client_hash("alice-pw-1234", "alice@example.com"),
        "new_password": derive_client_hash("new-pw", "alice@example.com"),
        HONEYPOT_FIELD: "",
    })
    assert resp.status_code == 302
    user.profile.refresh_from_db()
    assert user.profile.must_change_password is False


@pytest.mark.django_db
def test_no_email_after_password_change(client, make_user, login_client):
    make_user(plaintext="alice-pw-1234")
    login_client()
    mail.outbox.clear()
    from apps.security.honeypot import HONEYPOT_FIELD
    client.post("/settings/password/", {
        "current_password": derive_client_hash("alice-pw-1234", "alice@example.com"),
        "new_password": derive_client_hash("new-pw", "alice@example.com"),
        HONEYPOT_FIELD: "",
    })
    assert mail.outbox == []
