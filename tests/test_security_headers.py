"""Spec §11, §12 — outbound link safety + security headers."""
import pytest
from django.test import override_settings


@pytest.mark.django_db
def test_csp_header_set_on_every_response(client, make_profile_with_scheduling):
    make_profile_with_scheduling(username="alice")
    for path in ["/", "/directory/", "/p/alice/", "/privacy/", "/terms/"]:
        resp = client.get(path)
        assert "Content-Security-Policy" in resp.headers, path
        csp = resp.headers["Content-Security-Policy"]
        for token in [
            "default-src 'self'",
            "img-src 'self' data:",
            "style-src 'self' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "script-src 'self'",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "form-action 'self'",
            "base-uri 'self'",
        ]:
            assert token in csp


@pytest.mark.django_db
def test_csp_header_on_404(client):
    resp = client.get("/no-such-url/")
    assert resp.status_code == 404
    assert "Content-Security-Policy" in resp.headers


@pytest.mark.django_db
def test_xframe_options_deny(client):
    resp = client.get("/")
    assert resp.headers.get("X-Frame-Options") == "DENY"


@pytest.mark.django_db
def test_referrer_policy_same_origin(client):
    resp = client.get("/")
    # Django's SecurityMiddleware sets this from SECURE_REFERRER_POLICY.
    assert resp.headers.get("Referrer-Policy") == "same-origin"


@pytest.mark.django_db
def test_x_content_type_options(client):
    resp = client.get("/")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"


@pytest.mark.django_db
def test_session_cookie_attrs(client, make_user, login_client):
    make_user(plaintext="alice-pw")
    login_client(plaintext="alice-pw")
    cookie = client.cookies.get("sessionid")
    if cookie is not None:
        # In test settings cookies are not secure (no HTTPS), but the SAMESITE/HTTPONLY
        # defaults should still be honoured.
        assert cookie["httponly"] is True or cookie["httponly"] == "True"
        assert cookie["samesite"].lower() == "lax"


@pytest.mark.django_db
def test_csrf_required_for_post_login(client, make_user):
    """Form POST without a CSRF token is rejected."""
    from django.test import Client
    c = Client(enforce_csrf_checks=True)
    make_user(plaintext="alice-pw")
    resp = c.post("/accounts/login/", {"email": "alice@example.com", "password": "x" * 64, "nickname_confirm": ""})
    assert resp.status_code in (403, 400)
