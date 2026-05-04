"""Spec §9 — operator management commands."""
import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command

from apps.users.client_hash import derive_client_hash

User = get_user_model()


@pytest.mark.django_db
def test_create_user_creates_regular_user(monkeypatch):
    mail.outbox.clear()
    call_command("create_user", "alice@example.com", "--password=alice-pw-1234")
    user = User.objects.get(email="alice@example.com")
    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.is_active is True
    assert user.profile.is_verified is False
    # Password matches what the JS would derive.
    assert user.check_password(derive_client_hash("alice-pw-1234", "alice@example.com")) is True
    assert mail.outbox == []


@pytest.mark.django_db
def test_create_user_login_round_trip(client):
    call_command("create_user", "alice@example.com", "--password=alice-pw-1234")
    from apps.security.honeypot import HONEYPOT_FIELD
    resp = client.post("/accounts/login/", {
        "email": "alice@example.com",
        "password": derive_client_hash("alice-pw-1234", "alice@example.com"),
        HONEYPOT_FIELD: "",
    })
    assert resp.status_code == 302  # logged in


@pytest.mark.django_db
def test_verify_user_toggles_flag():
    call_command("create_user", "alice@example.com", "--password=pw")
    user = User.objects.get(email="alice@example.com")
    assert user.profile.is_verified is False
    call_command("verify_user", "alice@example.com")
    user.profile.refresh_from_db()
    assert user.profile.is_verified is True
    call_command("verify_user", "alice@example.com", "--unverify")
    user.profile.refresh_from_db()
    assert user.profile.is_verified is False


@pytest.mark.django_db
def test_reset_password_sets_must_change_and_new_pw(client):
    mail.outbox.clear()
    call_command("create_user", "alice@example.com", "--password=old-pw")
    call_command("reset_password", "alice@example.com", "--password=temp-pw")
    user = User.objects.get(email="alice@example.com")
    assert user.profile.must_change_password is True
    # Old password no longer works.
    assert user.check_password(derive_client_hash("old-pw", "alice@example.com")) is False
    # Temp works.
    assert user.check_password(derive_client_hash("temp-pw", "alice@example.com")) is True
    assert mail.outbox == []


@pytest.mark.django_db
def test_shell_qs_update_is_verified_equivalent_to_command():
    """A shell-level QuerySet.update on Profile.is_verified produces the same effect."""
    from apps.directory.models import Profile
    call_command("create_user", "alice@example.com", "--password=pw")
    Profile.objects.filter(user__email__iexact="alice@example.com").update(is_verified=True)
    user = User.objects.get(email="alice@example.com")
    assert user.profile.is_verified is True


@pytest.mark.django_db
def test_deactivate_recipe_excludes_from_directory(client, make_profile_with_scheduling):
    p = make_profile_with_scheduling(username="alice", first_name="Alice")
    User.objects.filter(email__iexact="alice@example.com").update(is_active=False)
    resp = client.get("/directory/")
    assert b"Alice" not in resp.content
    resp2 = client.get("/p/alice/")
    assert resp2.status_code == 404


@pytest.mark.django_db
def test_hard_delete_recipe_cascades(make_profile_with_scheduling):
    from apps.directory.models import Profile, ProviderService, ServiceCategory
    p = make_profile_with_scheduling(username="alice")
    cat = ServiceCategory.objects.get(slug="mock-interview")
    ProviderService.objects.create(profile=p, category=cat, custom_description="x")
    User.objects.filter(email__iexact="alice@example.com").delete()
    assert User.objects.filter(email__iexact="alice@example.com").count() == 0
    assert Profile.objects.filter(user__email__iexact="alice@example.com").count() == 0
    assert ProviderService.objects.filter(profile__user__email__iexact="alice@example.com").count() == 0
