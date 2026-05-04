"""Spec §7 — operator forgot-password flow forces password change on next request."""
import pytest

from apps.users.client_hash import derive_client_hash


@pytest.mark.django_db
def test_must_change_password_redirects_other_pages(client, make_user, login_client):
    user = make_user(plaintext="alice-pw-1234")
    user.profile.must_change_password = True
    user.profile.save()
    login_client()
    # Going anywhere other than /settings/password/ or /accounts/logout/ redirects to /settings/password/.
    for path in ["/settings/", "/", "/directory/"]:
        resp = client.get(path)
        assert resp.status_code == 302
        assert "/settings/password/" in resp.headers["Location"]


@pytest.mark.django_db
def test_must_change_password_allows_change_password_and_logout(client, make_user, login_client):
    user = make_user(plaintext="alice-pw-1234")
    user.profile.must_change_password = True
    user.profile.save()
    login_client()
    resp = client.get("/settings/password/")
    assert resp.status_code == 200
    resp2 = client.post("/accounts/logout/")
    assert resp2.status_code == 302
    assert resp2.headers["Location"] == "/"


@pytest.mark.django_db
def test_after_password_change_redirect_lifted(client, make_user, login_client):
    user = make_user(plaintext="alice-pw-1234")
    user.profile.must_change_password = True
    user.profile.save()
    login_client()
    from apps.security.honeypot import HONEYPOT_FIELD
    resp = client.post("/settings/password/", {
        "current_password": derive_client_hash("alice-pw-1234", "alice@example.com"),
        "new_password": derive_client_hash("new-pw-2345", "alice@example.com"),
        HONEYPOT_FIELD: "",
    })
    assert resp.status_code == 302
    user.profile.refresh_from_db()
    assert user.profile.must_change_password is False
    # Subsequent /settings/ request should not redirect to /settings/password/.
    resp2 = client.get("/settings/")
    assert resp2.status_code == 200
