"""Spec §10 (signals) and §4 (profile editing)."""
import pytest
from django.contrib.auth import get_user_model

from apps.directory.models import Profile, ProviderService, ServiceCategory
from tests.conftest import hex_hash

User = get_user_model()


@pytest.mark.django_db
def test_post_save_creates_profile():
    user = User(username="bob", email="bob@example.com", is_active=True)
    user.set_password("xx")
    user.save()
    assert Profile.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_post_save_does_not_duplicate_profile_on_resave(make_user):
    user = make_user()
    user.is_active = False
    user.save()  # Should not raise IntegrityError
    user.is_active = True
    user.save()
    assert Profile.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_new_profile_defaults_unverified(make_user):
    user = make_user()
    assert user.profile.is_verified is False
    assert user.profile.must_change_password is False
    assert user.profile.bio == ""
    assert user.profile.scheduling_url == ""
    assert user.profile.feedback_url == ""


@pytest.mark.django_db
def test_profile_edit_form_does_not_have_username_email_or_is_verified(client, make_user, login_client):
    user = make_user()
    login_client()
    resp = client.get("/settings/")
    assert resp.status_code == 200
    body = resp.content.decode()
    # No username/email/is_verified inputs in the rendered form.
    assert 'name="username"' not in body
    assert 'name="email"' not in body
    assert 'name="is_verified"' not in body


@pytest.mark.django_db
def test_profile_edit_post_ignores_privileged_fields(client, make_user, login_client):
    user = make_user()
    login_client()
    payload = _full_settings_payload(
        first_name="Alice",
        last_name="Anderson",
        bio="Lots of community service over the years and happy to mentor.",
        scheduling_url="https://calendly.com/alice/30",
        feedback_url="",
        extra={"username": "newname", "email": "new@example.com", "is_verified": "true"},
    )
    resp = client.post("/settings/", payload)
    assert resp.status_code == 302
    user.refresh_from_db()
    assert user.username == "alice"
    assert user.email == "alice@example.com"
    assert user.profile.is_verified is False


@pytest.mark.django_db
def test_first_name_required(client, make_user, login_client):
    make_user()
    login_client()
    payload = _full_settings_payload(
        first_name="",
        last_name="",
        bio="A long enough bio here.... lorem ipsum and more.",
        scheduling_url="",
    )
    resp = client.post("/settings/", payload)
    assert resp.status_code == 200
    assert b"first" in resp.content.lower() or b"required" in resp.content.lower() or b"enter" in resp.content.lower()


@pytest.mark.django_db
def test_last_name_optional(client, make_user, login_client):
    user = make_user()
    login_client()
    payload = _full_settings_payload(
        first_name="Alice",
        last_name="",
        bio="A community member offering thoughtful conversation today.",
        scheduling_url="",
    )
    resp = client.post("/settings/", payload)
    assert resp.status_code == 302
    user.refresh_from_db()
    assert user.profile.first_name == "Alice"
    assert user.profile.last_name == ""
    assert user.profile.display_name == "Alice"  # no trailing space


@pytest.mark.django_db
def test_bio_under_20_chars_rejected(client, make_user, login_client):
    make_user()
    login_client()
    payload = _full_settings_payload(
        first_name="Alice", last_name="", bio="too short", scheduling_url="",
    )
    resp = client.post("/settings/", payload)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_bio_strips_html(client, make_user, login_client):
    user = make_user()
    login_client()
    payload = _full_settings_payload(
        first_name="Alice", last_name="",
        bio="<b>kind</b> mentor for the community for many years now",
        scheduling_url="",
    )
    resp = client.post("/settings/", payload)
    assert resp.status_code == 302, resp.content
    user.refresh_from_db()
    assert "<b>" not in user.profile.bio
    assert "kind" in user.profile.bio


@pytest.mark.django_db
def test_first_name_collapses_whitespace(client, make_user, login_client):
    user = make_user()
    login_client()
    payload = _full_settings_payload(
        first_name="  Alice   Marie  ",
        last_name="\tAnderson\t  Smith ",
        bio="A community member offering thoughtful conversation today.",
        scheduling_url="",
    )
    resp = client.post("/settings/", payload)
    assert resp.status_code == 302
    user.refresh_from_db()
    assert user.profile.first_name == "Alice Marie"
    assert user.profile.last_name == "Anderson Smith"


@pytest.mark.django_db
def test_scheduling_url_rejects_javascript(client, make_user, login_client):
    user = make_user()
    login_client()
    payload = _full_settings_payload(
        first_name="Alice", last_name="",
        bio="A community member offering thoughtful conversation today.",
        scheduling_url="javascript:alert(1)",
    )
    resp = client.post("/settings/", payload)
    assert resp.status_code == 200
    user.refresh_from_db()
    assert user.profile.scheduling_url == ""


@pytest.mark.django_db
def test_feedback_url_optional_blank(client, make_user, login_client):
    user = make_user()
    login_client()
    payload = _full_settings_payload(
        first_name="Alice", last_name="",
        bio="A community member offering thoughtful conversation today.",
        scheduling_url="https://calendly.com/me",
        feedback_url="",
    )
    resp = client.post("/settings/", payload)
    assert resp.status_code == 302


@pytest.mark.django_db
def test_feedback_url_accepts_any_https_host(client, make_user, login_client):
    user = make_user()
    login_client()
    payload = _full_settings_payload(
        first_name="Alice", last_name="",
        bio="A community member offering thoughtful conversation today.",
        scheduling_url="https://calendly.com/me",
        feedback_url="https://random-tool.example/forms/abc",
    )
    resp = client.post("/settings/", payload)
    assert resp.status_code == 302


@pytest.mark.django_db
def test_anonymous_settings_redirects_to_login(client):
    resp = client.get("/settings/")
    assert resp.status_code == 302
    assert "/accounts/login/" in resp.headers["Location"]


def _full_settings_payload(*, first_name, last_name, bio, scheduling_url, feedback_url="", extra=None, services=None):
    """Helper: full POST body for the /settings/ view (including formset management form)."""
    services = services or []
    data = {
        "first_name": first_name,
        "last_name": last_name,
        "bio": bio,
        "scheduling_url": scheduling_url,
        "feedback_url": feedback_url,
        "providerservice_set-TOTAL_FORMS": str(len(services)),
        "providerservice_set-INITIAL_FORMS": "0",
        "providerservice_set-MIN_NUM_FORMS": "0",
        "providerservice_set-MAX_NUM_FORMS": "12",
    }
    for i, svc in enumerate(services):
        data[f"providerservice_set-{i}-id"] = ""
        data[f"providerservice_set-{i}-profile"] = ""
        data[f"providerservice_set-{i}-category"] = str(svc["category"])
        data[f"providerservice_set-{i}-custom_description"] = svc.get("custom_description", "")
    if extra:
        data.update(extra)
    return data


@pytest.mark.django_db
def test_predefined_service_with_description_saves(client, make_user, login_client):
    user = make_user()
    login_client()
    cat = ServiceCategory.objects.get(slug="mock-interview")
    payload = _full_settings_payload(
        first_name="Alice", last_name="",
        bio="A community member offering thoughtful conversation today.",
        scheduling_url="https://calendly.com/me/30",
        services=[{"category": cat.id, "custom_description": "I mentor early-career engineers"}],
    )
    resp = client.post("/settings/", payload)
    assert resp.status_code == 302, resp.content
    saved = user.profile.providerservice_set.get(category=cat)
    assert saved.custom_description == "I mentor early-career engineers"
    assert saved.is_freetext is False


@pytest.mark.django_db
def test_other_category_requires_description(client, make_user, login_client):
    user = make_user()
    login_client()
    other = ServiceCategory.objects.get(slug="other")
    payload = _full_settings_payload(
        first_name="Alice", last_name="",
        bio="A community member offering thoughtful conversation today.",
        scheduling_url="",
        services=[{"category": other.id, "custom_description": "    "}],
    )
    resp = client.post("/settings/", payload)
    assert resp.status_code == 200  # rejected with form error, not 500


@pytest.mark.django_db
def test_predefined_category_no_description_accepted(client, make_user, login_client):
    user = make_user()
    login_client()
    cat = ServiceCategory.objects.get(slug="mock-interview")
    payload = _full_settings_payload(
        first_name="Alice", last_name="",
        bio="A community member offering thoughtful conversation today.",
        scheduling_url="",
        services=[{"category": cat.id, "custom_description": ""}],
    )
    resp = client.post("/settings/", payload)
    assert resp.status_code == 302


@pytest.mark.django_db
def test_formset_idor_protection(client, make_user, login_client, make_profile_with_scheduling):
    """A POST with a service-row PK belonging to another profile must be rejected."""
    other = make_profile_with_scheduling(username="bob", email="bob@example.com")
    bob_cat = ServiceCategory.objects.get(slug="mock-interview")
    other_svc = ProviderService.objects.create(profile=other, category=bob_cat, is_freetext=False)

    user = make_user(username="alice", email="alice@example.com", plaintext="alice-pw")
    login_client(email="alice@example.com", plaintext="alice-pw")

    cat = ServiceCategory.objects.get(slug="quran-revising")
    payload = _full_settings_payload(
        first_name="Alice", last_name="",
        bio="A community member offering thoughtful conversation today.",
        scheduling_url="",
        services=[{"category": cat.id, "custom_description": ""}],
    )
    payload["providerservice_set-0-id"] = str(other_svc.id)  # crafted IDOR

    resp = client.post("/settings/", payload)
    # Either form is rejected (200) OR the foreign row is left untouched (302 + no mutation).
    other_svc.refresh_from_db()
    assert other_svc.profile_id == other.id
    assert other_svc.category_id == bob_cat.id


@pytest.mark.django_db
def test_formset_rejects_total_forms_above_12(client, make_user, login_client):
    user = make_user()
    login_client()
    cat = ServiceCategory.objects.get(slug="mock-interview")
    data = {
        "first_name": "Alice", "last_name": "",
        "bio": "A community member offering thoughtful conversation today.",
        "scheduling_url": "", "feedback_url": "",
        "providerservice_set-TOTAL_FORMS": "13",
        "providerservice_set-INITIAL_FORMS": "0",
        "providerservice_set-MIN_NUM_FORMS": "0",
        "providerservice_set-MAX_NUM_FORMS": "12",
    }
    for i in range(13):
        data[f"providerservice_set-{i}-id"] = ""
        data[f"providerservice_set-{i}-profile"] = ""
        data[f"providerservice_set-{i}-category"] = str(cat.id)
        data[f"providerservice_set-{i}-custom_description"] = f"row {i}"
    resp = client.post("/settings/", data)
    assert resp.status_code == 200  # rejected, not 302
    assert user.profile.providerservice_set.count() == 0
