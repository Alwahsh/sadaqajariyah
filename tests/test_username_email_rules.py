"""Spec §2.2 / §2.3 — username and email rules."""
import pytest
from django.contrib.auth import get_user_model

from apps.users.reserved import RESERVED_USERNAMES

User = get_user_model()


@pytest.mark.django_db
def test_registration_lowercases_username_and_email(client, signup_post_payload):
    resp = client.post("/accounts/signup/", signup_post_payload(
        username="Ahmed", email="Foo@Example.com", plaintext="abc-1234567890"))
    assert resp.status_code == 302
    user = User.objects.get(username="ahmed")
    assert user.email == "foo@example.com"


@pytest.mark.django_db
def test_registration_rejects_mixedcase_duplicate_username(client, signup_post_payload, make_user):
    make_user(username="ahmed", email="first@example.com")
    resp = client.post("/accounts/signup/", signup_post_payload(
        username="AHMED", email="second@example.com", plaintext="abc-1234567890"))
    assert resp.status_code == 200  # form re-rendered with errors
    assert User.objects.filter(email="second@example.com").count() == 0


@pytest.mark.django_db
def test_registration_rejects_mixedcase_duplicate_email(client, signup_post_payload, make_user):
    make_user(username="user1", email="foo@example.com")
    resp = client.post("/accounts/signup/", signup_post_payload(
        username="user2", email="Foo@Example.com", plaintext="abc-1234567890"))
    assert resp.status_code == 200
    assert User.objects.filter(username="user2").count() == 0


@pytest.mark.parametrize("name", sorted(RESERVED_USERNAMES))
@pytest.mark.django_db
def test_registration_rejects_reserved_usernames(client, signup_post_payload, name):
    resp = client.post("/accounts/signup/", signup_post_payload(
        username=name, email="someone@example.com", plaintext="abc-1234567890"))
    assert resp.status_code == 200
    assert User.objects.filter(username=name).count() == 0


@pytest.mark.django_db
def test_registration_rejects_non_ascii_username(client, signup_post_payload):
    resp = client.post("/accounts/signup/", signup_post_payload(
        username="naïve", email="naive@example.com", plaintext="abc-1234567890"))
    assert resp.status_code == 200
    assert User.objects.filter(email="naive@example.com").count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("u", ["ab", "_alice", "-alice", "x" * 31])
def test_registration_rejects_bad_format_username(client, signup_post_payload, u):
    resp = client.post("/accounts/signup/", signup_post_payload(
        username=u, email="ok@example.com", plaintext="abc-1234567890"))
    assert resp.status_code == 200
    assert User.objects.filter(email="ok@example.com").count() == 0


@pytest.mark.django_db
def test_signal_lowercases_username_and_email_on_shell_path():
    """pre_save signal lowercases username and email even via raw User.objects.create."""
    user = User(username="MixedCase", email="Mixed@Example.com", is_active=True)
    user.set_password("xx")
    user.save()
    user.refresh_from_db()
    assert user.username == "mixedcase"
    assert user.email == "mixed@example.com"
