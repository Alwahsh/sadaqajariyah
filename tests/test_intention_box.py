"""The registration page must show the intention-setting message before the
form. Pinning the exact copy here means a future template refactor can't
silently drop or soften the message.
"""
import re
from pathlib import Path

import pytest

from django.conf import settings


# The exact copy the user wants on the registration page. Apostrophes are
# fine — the test asserts substrings around them so HTML auto-escape doesn't
# break the match.
INTENTION_FRAGMENTS = [
    "Take a minute to set your intentions",
    "visualize the reward you get from helping someone for free for the sake of Allah",
    "you get reward for everytime they use it",
    "everytime someone benefits from them because of it",
    "better reward than any recognition you can get in this life",
    "focus on this idea while creating your account",
]


@pytest.mark.django_db
def test_intention_box_present_on_signup(client):
    resp = client.get("/accounts/signup/")
    assert resp.status_code == 200
    body = resp.content.decode()
    assert 'data-test="intention-box"' in body, (
        "registration page is missing the intention-box element"
    )


@pytest.mark.django_db
def test_intention_box_copy_verbatim(client):
    """Each of the six load-bearing phrases must appear in the rendered page —
    if any are missing, the message has been altered."""
    resp = client.get("/accounts/signup/")
    body = resp.content.decode()
    missing = [frag for frag in INTENTION_FRAGMENTS if frag not in body]
    assert not missing, (
        f"intention-box copy is missing or altered. Missing fragments: {missing}"
    )


@pytest.mark.django_db
def test_intention_box_appears_before_form(client):
    """The box must render before the registration form, not after — so
    visitors read it before filling fields."""
    resp = client.get("/accounts/signup/")
    body = resp.content.decode()
    box_idx = body.find('data-test="intention-box"')
    form_idx = body.find('<form ')
    assert box_idx > 0
    assert form_idx > 0
    assert box_idx < form_idx, (
        "intention-box must appear above the registration form, not below it"
    )


@pytest.mark.django_db
def test_intention_box_only_on_signup(client, make_user, login_client):
    """The box is registration-specific. Login, settings, home, etc. must NOT
    show it (otherwise it loses its weight)."""
    paths = ["/", "/directory/", "/accounts/login/", "/privacy/", "/terms/"]
    for path in paths:
        resp = client.get(path)
        body = resp.content.decode()
        assert 'data-test="intention-box"' not in body, (
            f"intention-box must not render on {path}"
        )

    make_user()
    login_client()
    resp = client.get("/settings/")
    assert 'data-test="intention-box"' not in resp.content.decode(), (
        "intention-box must not render on /settings/"
    )


def test_intention_box_styled_in_stylesheet():
    """The box has its own CSS rule using the sage palette (not the warning
    palette) — without the rule it renders as plain unstyled text or worse,
    looks like an error."""
    text = Path(settings.BASE_DIR, "static", "styles.css").read_text()
    assert ".intention-box" in text
    # Locate the rule and inspect its properties.
    m = re.search(r"\.intention-box\s*\{([^}]+)\}", text)
    assert m, "stylesheet missing .intention-box rule"
    block = m.group(1)
    # The box should NOT use the warning palette (warm-yellow) — that would
    # mis-frame the message as a warning.
    assert "#FBF1D6" not in block, "intention-box must not use the warning palette"
    # Should use the sage palette in some form.
    assert "--sageSoft" in block or "--sageDeep" in block or "#D9E4D6" in block, (
        "intention-box should use the sage palette for a contemplative tone"
    )
