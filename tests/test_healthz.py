"""The /healthz endpoint is the production health probe path. It must be:
  - cheap (no template rendering, no auth, no DB-heavy queries)
  - correct (200 with body "ok" when the DB is reachable)
  - resilient against the must-change-password redirect
  - reachable both with and without a trailing slash (Render configures one path)
"""
from unittest.mock import patch

import pytest


@pytest.mark.django_db
def test_healthz_returns_ok(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.content == b"ok"


@pytest.mark.django_db
def test_healthz_content_type_plain(client):
    resp = client.get("/healthz")
    assert resp.headers["Content-Type"].startswith("text/plain")


@pytest.mark.django_db
def test_healthz_with_trailing_slash(client):
    """Render's path config can be either /healthz or /healthz/. Both must work
    without going through APPEND_SLASH's 301 (which would log a redirect every
    probe and waste a round-trip)."""
    resp = client.get("/healthz/")
    assert resp.status_code == 200
    assert resp.content == b"ok"


@pytest.mark.django_db
def test_healthz_without_trailing_slash_no_redirect(client):
    """The probe path must resolve directly — no 301 to a slashed variant."""
    resp = client.get("/healthz")
    assert resp.status_code == 200, (
        "GET /healthz should return 200 directly; got "
        f"{resp.status_code}. If this is a redirect, register the no-slash path explicitly."
    )


@pytest.mark.django_db
def test_healthz_does_not_render_html(client):
    """Probes shouldn't pull the heavy base template (Google Fonts CSS, nav, footer)."""
    resp = client.get("/healthz")
    body = resp.content.decode()
    assert "<html" not in body.lower()
    assert "fonts.googleapis.com" not in body
    assert "Sadaqa Jariyah" not in body  # nav wordmark


@pytest.mark.django_db
def test_healthz_does_not_require_auth(client):
    """No login required — the probe is unauthenticated."""
    resp = client.get("/healthz")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_healthz_returns_503_when_db_down(client):
    """When the DB connection raises, the endpoint must report unhealthy
    (503) so Render takes the instance out of rotation instead of routing
    traffic to a broken process."""
    from apps.pages import views

    class _BadConn:
        def cursor(self):
            raise RuntimeError("simulated DB outage")

    with patch.object(views, "connection", _BadConn()):
        resp = client.get("/healthz")
    assert resp.status_code == 503
    assert b"db unavailable" in resp.content


@pytest.mark.django_db
def test_healthz_exempt_from_must_change_password_redirect(
    client, make_user, login_client,
):
    """An authenticated user with must_change_password=True normally has every
    path bounce to /settings/password/. The health probe must be exempt — so
    a residual session in dev or a probe running with cookies still works."""
    user = make_user()
    user.profile.must_change_password = True
    user.profile.save()
    login_client()
    resp = client.get("/healthz")
    assert resp.status_code == 200, (
        "must_change_password redirect should not apply to /healthz"
    )


@pytest.mark.django_db
def test_healthz_path_is_reserved_username():
    """A member must not be able to register `healthz` as a username and shadow
    the probe via /p/healthz/. The path itself doesn't collide with /p/<username>/,
    but the reservation removes the chance of confusion."""
    from apps.users.reserved import RESERVED_USERNAMES
    assert "healthz" in RESERVED_USERNAMES
