"""The site-wide disclaimer banner must render on every page so visitors are
framed before reading any profile. Pinning the exact copy here means a future
template refactor can't accidentally drop it."""
import pytest

DISCLAIMER_TEXT = (
    "Services provided here are by volunteers and for free. "
    "None of the services has a guaranteed quality or reliability. "
    "Use at your own discretion if you trust the experience of the member giving you the service."
)


@pytest.mark.django_db
@pytest.mark.parametrize("path", [
    "/",
    "/directory/",
    "/privacy/",
    "/terms/",
    "/accounts/login/",
    "/accounts/signup/",
])
def test_disclaimer_present_on_anonymous_pages(client, path):
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} returned {resp.status_code}"
    body = resp.content.decode()
    assert 'data-test="site-disclaimer"' in body, (
        f"{path} is missing the site-disclaimer banner element"
    )
    assert DISCLAIMER_TEXT in body, (
        f"{path} is missing the disclaimer copy verbatim"
    )


@pytest.mark.django_db
def test_disclaimer_present_on_public_profile(client, make_profile_with_scheduling):
    make_profile_with_scheduling(username="alice")
    resp = client.get("/p/alice/")
    body = resp.content.decode()
    assert 'data-test="site-disclaimer"' in body
    assert DISCLAIMER_TEXT in body


@pytest.mark.django_db
def test_disclaimer_present_on_settings_for_logged_in_user(client, make_user, login_client):
    make_user()
    login_client()
    resp = client.get("/settings/")
    body = resp.content.decode()
    assert 'data-test="site-disclaimer"' in body
    assert DISCLAIMER_TEXT in body


@pytest.mark.django_db
def test_disclaimer_present_on_change_password_page(client, make_user, login_client):
    make_user()
    login_client()
    resp = client.get("/settings/password/")
    body = resp.content.decode()
    assert 'data-test="site-disclaimer"' in body
    assert DISCLAIMER_TEXT in body


@pytest.mark.django_db
def test_disclaimer_present_on_404(client):
    resp = client.get("/this-route-does-not-exist/")
    assert resp.status_code == 404
    body = resp.content.decode()
    assert 'data-test="site-disclaimer"' in body
    assert DISCLAIMER_TEXT in body


def test_disclaimer_styled_in_stylesheet():
    """The disclaimer banner has its own CSS rule using the warm-yellow caution
    palette — without the rule it would render as plain unstyled text."""
    from pathlib import Path
    from django.conf import settings
    text = Path(settings.BASE_DIR, "static", "styles.css").read_text()
    assert ".site-disclaimer" in text, "stylesheet missing .site-disclaimer rule"
    # Caution palette tokens — at least one must appear in the rule's vicinity.
    idx = text.find(".site-disclaimer")
    block = text[idx:idx + 2000]
    assert "--warnBg" in block or "#FBF1D6" in block, (
        "site-disclaimer should use the warm-yellow caution palette"
    )
