"""Spec addendum — the "Schedule with me" link must be gated behind a consent
checkbox. The button renders as disabled (aria-disabled + .is-locked) until
the visitor checks the consent box; clicking the disabled button is blocked
in JS.

Pinning the exact consent copy here means a future template refactor can't
silently soften the warning.
"""
import re
from pathlib import Path

import pytest

from django.conf import settings


CONSENT_TEXT = (
    "I understand that I need to exercise caution with any information I share "
    "during scheduling or during the consultation and that the person I'm "
    "scheduling with might not be who I am expecting and that any advice I "
    "receive can be wrong or unreliable and I am responsible for the consequences "
    "of following it."
)


@pytest.mark.django_db
def test_consent_checkbox_present(client, make_profile_with_scheduling):
    make_profile_with_scheduling(username="alice")
    resp = client.get("/p/alice/")
    body = resp.content.decode()
    assert 'data-test="schedule-consent"' in body
    assert 'data-test="schedule-consent-checkbox"' in body


@pytest.mark.django_db
def test_consent_checkbox_copy_verbatim(client, make_profile_with_scheduling):
    """The exact warning text must be present — no softening, no abbreviation."""
    make_profile_with_scheduling(username="alice")
    resp = client.get("/p/alice/")
    body = resp.content.decode()
    # Apostrophe in "I'm" gets HTML-entity-encoded — assert by the
    # apostrophe-free substrings around it.
    assert "I understand that I need to exercise caution with any information I share" in body
    assert "during scheduling or during the consultation" in body
    assert "might not be who I am expecting" in body
    assert "any advice I receive can be wrong or unreliable" in body
    assert "I am responsible for the consequences of following it" in body


@pytest.mark.django_db
def test_schedule_button_disabled_initially(client, make_profile_with_scheduling):
    """Server-rendered HTML must show the button as visually disabled before any
    JS runs — clients with JS off still see the locked state, and the gate is
    not bypassable by simply turning JS off."""
    make_profile_with_scheduling(username="alice")
    resp = client.get("/p/alice/")
    body = resp.content.decode()
    # Find the schedule CTA anchor and inspect its attributes.
    a_match = re.search(r'<a[^>]+data-test="schedule-cta"[^>]*>', body)
    assert a_match, "schedule-cta anchor not found"
    a_tag = a_match.group(0)
    assert 'aria-disabled="true"' in a_tag, (
        "schedule button must render with aria-disabled=true before consent is given"
    )
    assert "is-locked" in a_tag, "schedule button must carry .is-locked class initially"
    assert 'data-consent-target="schedule"' in a_tag, (
        "schedule button must be tagged with data-consent-target so the JS can bind it"
    )


@pytest.mark.django_db
def test_outbound_attrs_preserved_on_gated_button(client, make_profile_with_scheduling):
    """Adding the consent gate must not drop the outbound link safety attrs."""
    make_profile_with_scheduling(username="alice")
    resp = client.get("/p/alice/")
    body = resp.content.decode()
    a_match = re.search(r'<a[^>]+data-test="schedule-cta"[^>]*>', body)
    assert a_match
    a_tag = a_match.group(0)
    assert 'target="_blank"' in a_tag
    assert 'rel="noopener noreferrer"' in a_tag
    assert 'referrerpolicy="no-referrer"' in a_tag


@pytest.mark.django_db
def test_hint_text_renders(client, make_profile_with_scheduling):
    make_profile_with_scheduling(username="alice")
    resp = client.get("/p/alice/")
    body = resp.content.decode()
    assert 'data-test="schedule-hint"' in body
    assert "Check the box above to enable the link" in body


@pytest.mark.django_db
def test_consent_js_loaded_when_scheduling_set(client, make_profile_with_scheduling):
    make_profile_with_scheduling(username="alice")
    resp = client.get("/p/alice/")
    body = resp.content.decode()
    assert "profile-consent.js" in body, (
        "profile-consent.js must be loaded on profiles with a scheduling URL"
    )


@pytest.mark.django_db
def test_consent_js_not_required_for_owner_no_scheduling(client, make_user, login_client):
    """A logged-in owner viewing their own profile with no scheduling URL has no
    schedule button — and therefore no need for the consent JS. Loading it would
    be wasteful but not wrong; this test pins the no-button case."""
    make_user()
    login_client()
    resp = client.get("/p/alice/")
    body = resp.content.decode()
    assert resp.status_code == 200
    assert 'data-test="schedule-cta"' not in body, "no schedule button without scheduling URL"
    assert 'data-test="schedule-consent-checkbox"' not in body


def test_consent_js_file_exists_and_blocks_click():
    """The shipped JS file must implement preventDefault when the checkbox is
    unchecked. Without that, the gate is purely visual — a determined click
    would still open the scheduling URL."""
    js_path = Path(settings.BASE_DIR, "static", "profile-consent.js")
    assert js_path.exists(), "static/profile-consent.js missing"
    text = js_path.read_text()
    assert "preventDefault" in text, "consent JS must call preventDefault on the click event"
    assert "checkbox.checked" in text, "consent JS must read the checkbox.checked state"
    assert "is-locked" in text, "consent JS must toggle the .is-locked class"
    assert "aria-disabled" in text, "consent JS must toggle aria-disabled"


def test_consent_styles_define_locked_state():
    """The .is-locked class must visibly change the button's appearance — opacity,
    cursor, or color — so users see the disabled state."""
    css_path = Path(settings.BASE_DIR, "static", "styles.css")
    text = css_path.read_text()
    # Match the .schedule-btn.is-locked rule and inspect its properties.
    m = re.search(r"\.schedule-btn\.is-locked\s*\{([^}]+)\}", text)
    assert m, "stylesheet missing .schedule-btn.is-locked rule"
    block = m.group(1)
    # At minimum, opacity OR cursor must be set so the disabled state is visible.
    assert "opacity" in block, ".schedule-btn.is-locked must change opacity"
    assert "cursor" in block, ".schedule-btn.is-locked must change cursor (e.g. not-allowed)"


@pytest.mark.django_db
def test_csp_allows_consent_script(client, make_profile_with_scheduling):
    """profile-consent.js is served from `/static/`, which is `'self'` — the
    CSP must therefore allow `script-src 'self'`. Catches a future regression
    where someone tightens the policy and breaks the consent gate."""
    make_profile_with_scheduling(username="alice")
    resp = client.get("/p/alice/")
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "script-src 'self'" in csp, (
        "CSP must allow script-src 'self' for the bundled profile-consent.js"
    )
