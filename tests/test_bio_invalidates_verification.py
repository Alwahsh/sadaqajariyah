"""Editing the bio resets the verified badge — the operator's vouching is
specifically for the bio content as it stood at verify time. Other field
changes (name, scheduling URL, services) do NOT touch verified status.

A currently-verified user editing /settings/ must see a warning explaining
this.
"""
import pytest

from apps.directory.models import ServiceCategory


def _settings_payload(*, first_name="Alice", last_name="",
                      bio="A community member offering thoughtful conversation today.",
                      scheduling_url="https://calendly.com/me/30",
                      feedback_url="",
                      total_forms="0", initial_forms="0", services=None):
    services = services or []
    data = {
        "first_name": first_name,
        "last_name": last_name,
        "bio": bio,
        "scheduling_url": scheduling_url,
        "feedback_url": feedback_url,
        "providerservice_set-TOTAL_FORMS": str(len(services) or int(total_forms)),
        "providerservice_set-INITIAL_FORMS": initial_forms,
        "providerservice_set-MIN_NUM_FORMS": "0",
        "providerservice_set-MAX_NUM_FORMS": "12",
    }
    for i, svc in enumerate(services):
        for k in ("id", "profile"):
            data[f"providerservice_set-{i}-{k}"] = str(svc.get(k, ""))
        data[f"providerservice_set-{i}-category"] = str(svc["category"])
        data[f"providerservice_set-{i}-custom_description"] = svc.get("custom_description", "")
        data[f"providerservice_set-{i}-DELETE"] = svc.get("delete", "")
    return data


# =========================================================================
# Bio change → unverify
# =========================================================================

@pytest.mark.django_db
def test_bio_change_unverifies_a_verified_user(client, make_profile_with_scheduling, login_client):
    p = make_profile_with_scheduling(
        username="alice",
        bio="The original bio that the operator already vouched for.",
        is_verified=True,
    )
    login_client(email="alice@example.com", plaintext="alice-pw-1234")
    payload = _settings_payload(
        first_name=p.first_name, last_name=p.last_name,
        bio="A completely new bio — the operator has not seen this yet.",
        scheduling_url=p.scheduling_url,
    )
    resp = client.post("/settings/", payload)
    assert resp.status_code == 302
    p.refresh_from_db()
    assert p.is_verified is False, (
        "editing the bio must reset is_verified to False"
    )


@pytest.mark.django_db
def test_bio_unchanged_keeps_verified_status(client, make_profile_with_scheduling, login_client):
    """Saving the form without altering the bio must NOT touch is_verified.
    The user might be saving a new scheduling URL or a different first name."""
    bio = "A community member offering thoughtful conversation today."
    p = make_profile_with_scheduling(
        username="alice", bio=bio, first_name="Alice",
        scheduling_url="https://calendly.com/me", is_verified=True,
    )
    login_client(email="alice@example.com", plaintext="alice-pw-1234")
    payload = _settings_payload(
        first_name="Alice Marie",  # changing first name only
        bio=bio,                   # bio identical
        scheduling_url="https://calendly.com/me",
    )
    resp = client.post("/settings/", payload)
    assert resp.status_code == 302
    p.refresh_from_db()
    assert p.is_verified is True, (
        "first-name change with no bio change must NOT unverify"
    )
    assert p.first_name == "Alice Marie"


@pytest.mark.django_db
def test_changing_scheduling_url_alone_does_not_unverify(client, make_profile_with_scheduling, login_client):
    bio = "A community member offering thoughtful conversation today."
    p = make_profile_with_scheduling(username="alice", bio=bio, is_verified=True)
    login_client(email="alice@example.com", plaintext="alice-pw-1234")
    payload = _settings_payload(
        first_name=p.first_name, bio=bio,
        scheduling_url="https://cal.com/me",  # changed
    )
    resp = client.post("/settings/", payload)
    assert resp.status_code == 302
    p.refresh_from_db()
    assert p.is_verified is True


@pytest.mark.django_db
def test_changing_services_alone_does_not_unverify(client, make_profile_with_scheduling, login_client):
    bio = "A community member offering thoughtful conversation today."
    p = make_profile_with_scheduling(username="alice", bio=bio, is_verified=True)
    cat = ServiceCategory.objects.get(slug="mock-interview")
    login_client(email="alice@example.com", plaintext="alice-pw-1234")
    payload = _settings_payload(
        first_name=p.first_name, bio=bio,
        scheduling_url=p.scheduling_url,
        services=[{"category": cat.id, "custom_description": "Senior engineers"}],
    )
    resp = client.post("/settings/", payload)
    assert resp.status_code == 302, resp.content[:1000]
    p.refresh_from_db()
    assert p.is_verified is True
    assert p.providerservice_set.count() == 1


@pytest.mark.django_db
def test_bio_change_for_unverified_user_is_a_noop(client, make_profile_with_scheduling, login_client):
    """If the user wasn't verified to begin with, a bio change just saves —
    no warning fires, no special branch."""
    p = make_profile_with_scheduling(
        username="alice",
        bio="The original bio.",
        is_verified=False,
    )
    login_client(email="alice@example.com", plaintext="alice-pw-1234")
    payload = _settings_payload(
        first_name=p.first_name,
        bio="A new bio I just wrote up to think it through more carefully.",
        scheduling_url=p.scheduling_url,
    )
    resp = client.post("/settings/", payload, follow=True)
    p.refresh_from_db()
    assert p.is_verified is False
    body = resp.content.decode()
    assert "verified badge has been removed" not in body, (
        "the unverify warning must NOT fire for a user who wasn't verified"
    )


@pytest.mark.django_db
def test_bio_change_unverify_fires_warning_message(client, make_profile_with_scheduling, login_client):
    """After a bio change that drops verified status, the next page render
    must show the explanatory messages.warning so the user knows why their
    badge is gone."""
    p = make_profile_with_scheduling(
        username="alice",
        bio="The original bio that the operator vouched for.",
        is_verified=True,
    )
    login_client(email="alice@example.com", plaintext="alice-pw-1234")
    payload = _settings_payload(
        first_name=p.first_name,
        bio="A wholly new bio that needs re-review by the operator.",
        scheduling_url=p.scheduling_url,
    )
    resp = client.post("/settings/", payload, follow=True)
    body = resp.content.decode()
    assert "verified badge has been removed" in body
    # Apostrophe is HTML-escaped — assert without it.
    assert "operator will re-verify your account" in body


# =========================================================================
# Heads-up banner on /settings/ for verified users
# =========================================================================

@pytest.mark.django_db
def test_warning_banner_renders_for_verified_user(client, make_profile_with_scheduling, login_client):
    make_profile_with_scheduling(username="alice", is_verified=True)
    login_client(email="alice@example.com", plaintext="alice-pw-1234")
    resp = client.get("/settings/")
    body = resp.content.decode()
    assert 'data-test="bio-edit-warning"' in body, (
        "verified user must see the bio-edit warning banner on /settings/"
    )
    assert "Editing your bio will remove the badge" in body


@pytest.mark.django_db
def test_warning_banner_absent_for_unverified_user(client, make_profile_with_scheduling, login_client):
    make_profile_with_scheduling(username="alice", is_verified=False)
    login_client(email="alice@example.com", plaintext="alice-pw-1234")
    resp = client.get("/settings/")
    body = resp.content.decode()
    assert 'data-test="bio-edit-warning"' not in body, (
        "unverified user must NOT see the bio-edit warning banner"
    )


@pytest.mark.django_db
def test_warning_banner_appears_above_bio_field(client, make_profile_with_scheduling, login_client):
    """The warning's job is to frame the bio field — it must come before it
    in the document, not after."""
    make_profile_with_scheduling(username="alice", is_verified=True)
    login_client(email="alice@example.com", plaintext="alice-pw-1234")
    resp = client.get("/settings/")
    body = resp.content.decode()
    warning_idx = body.find('data-test="bio-edit-warning"')
    bio_idx = body.find('name="bio"')
    assert warning_idx >= 0 and bio_idx >= 0
    assert warning_idx < bio_idx, (
        "bio-edit warning must appear above the bio textarea, not below it"
    )


def test_bio_warning_styled_in_stylesheet():
    """The .bio-verified-warning rule must exist and use the warm-yellow
    caution palette."""
    import re
    from pathlib import Path
    from django.conf import settings
    text = Path(settings.BASE_DIR, "static", "styles.css").read_text()
    assert ".bio-verified-warning" in text, "stylesheet missing .bio-verified-warning rule"
    m = re.search(r"\.bio-verified-warning\s*\{([^}]+)\}", text)
    assert m
    block = m.group(1)
    assert "--warnBg" in block or "#FBF1D6" in block
