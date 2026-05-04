"""Spec §10 — DB-level constraints. Some are Postgres-only; we skip those on SQLite."""
import pytest
from django.db import IntegrityError, connection, transaction

from apps.directory.models import ProviderService, ServiceCategory


def _is_postgres():
    return connection.vendor == "postgresql"


@pytest.mark.django_db
def test_freetext_requires_description():
    other = ServiceCategory.objects.get(slug="other")
    profile_user_setup = _profile_factory()
    profile = profile_user_setup()
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ps = ProviderService(profile=profile, category=other, custom_description="")
            # Bypass the model's save() override that mirrors is_freetext from category.
            ps.is_freetext = True
            ps.custom_description = ""
            ProviderService.objects.bulk_create([ps])


@pytest.mark.django_db
def test_non_freetext_with_description_accepted():
    cat = ServiceCategory.objects.get(slug="mock-interview")
    profile = _profile_factory()()
    ps = ProviderService.objects.create(
        profile=profile, category=cat,
        custom_description="I mentor early-career engineers",
    )
    assert ps.pk is not None
    assert ps.is_freetext is False


@pytest.mark.django_db
def test_uniq_profile_category_nonfreetext_constraint():
    cat = ServiceCategory.objects.get(slug="mock-interview")
    profile = _profile_factory()()
    ProviderService.objects.create(profile=profile, category=cat)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ProviderService.objects.create(profile=profile, category=cat)


@pytest.mark.django_db
def test_uniq_service_category_other_freetext_constraint():
    """A second is_other_freetext=True row is rejected."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ServiceCategory.objects.create(name="Other 2", slug="other-2", is_other_freetext=True)


@pytest.mark.django_db
def test_seed_migration_created_categories():
    """Categories from the seed migration exist."""
    assert ServiceCategory.objects.filter(slug="mock-interview").exists()
    assert ServiceCategory.objects.filter(slug="other", is_other_freetext=True).exists()
    assert ServiceCategory.objects.filter(is_other_freetext=True).count() == 1


def _profile_factory():
    """Return a callable that creates a fresh user+profile for tests in this module."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    counter = {"n": 0}

    def _make():
        counter["n"] += 1
        u = User(username=f"db{counter['n']}", email=f"db{counter['n']}@example.com", is_active=True)
        u.set_password("xx")
        u.save()
        return u.profile
    return _make
