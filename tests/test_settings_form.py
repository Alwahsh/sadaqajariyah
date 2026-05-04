"""Regression: the /settings/ page must render an editable services formset
with the seeded categories. Past bug: extra=0 on the formset gave fresh users
zero blank rows and no way to add services from the UI.
"""
import re

import pytest

from apps.directory.models import ServiceCategory


@pytest.mark.django_db
def test_settings_renders_max_blank_service_rows_for_new_user(client, make_user, login_client):
    """A fresh user can fill any number of services up to the 12-row cap in
    one save, so the form renders 12 blank rows."""
    make_user()
    login_client()
    resp = client.get("/settings/")
    body = resp.content.decode()
    rows = body.count('data-test="service-row"')
    assert rows == 12, (
        f"Fresh users must see 12 blank service rows (the formset's max_num cap). "
        f"Got {rows}."
    )


@pytest.mark.django_db
def test_settings_total_rows_caps_at_12(client, make_profile_with_scheduling, login_client):
    """A user with N existing services sees N existing rows + (12-N) blanks."""
    from apps.directory.models import ProviderService
    p = make_profile_with_scheduling(username="alice")
    cats = list(ServiceCategory.objects.filter(is_active=True, is_other_freetext=False)[:2])
    for c in cats:
        ProviderService.objects.create(profile=p, category=c)
    login_client(email="alice@example.com", plaintext="alice-pw-1234")
    resp = client.get("/settings/")
    body = resp.content.decode()
    rows = body.count('data-test="service-row"')
    assert rows == 12, f"Total rows should sum to 12 cap, got {rows}"


@pytest.mark.django_db
def test_category_dropdown_includes_all_seeded_categories(client, make_user, login_client):
    """Every active seeded category appears as an <option> in the category select."""
    make_user()
    login_client()
    resp = client.get("/settings/")
    body = resp.content.decode()
    for cat in ServiceCategory.objects.filter(is_active=True):
        # Look for the option text (escaped if needed). Use a relaxed match
        # because the apostrophe in "Qur'an Tutoring" is HTML-entity-encoded.
        # The id-keyed lookup is the robust check.
        pattern = re.compile(rf'<option value="{cat.id}"[^>]*>')
        assert pattern.search(body), f"category {cat.slug} (id={cat.id}) missing from dropdown"


@pytest.mark.django_db
def test_seed_migration_creates_canonical_categories():
    """The data migrations are the only path that creates categories — verify
    the canonical v1 list (synced with apps/directory/migrations/0003) is present."""
    assert ServiceCategory.objects.filter(is_other_freetext=True).count() == 1
    expected_slugs = {"arabic-language", "mock-interview", "quran-revising", "other"}
    actual = set(ServiceCategory.objects.values_list("slug", flat=True))
    missing = expected_slugs - actual
    assert not missing, f"seed migration is missing categories: {missing}"


@pytest.mark.django_db
def test_user_with_existing_services_gets_blank_rows_up_to_12(client, make_profile_with_scheduling, login_client):
    """A user who already has services should see their existing rows plus blank rows
    until total reaches 12 (the formset cap)."""
    from apps.directory.models import ProviderService
    p = make_profile_with_scheduling(username="alice")
    cat = ServiceCategory.objects.get(slug="mock-interview")
    ProviderService.objects.create(profile=p, category=cat, custom_description="early-career mentoring")
    login_client(email="alice@example.com", plaintext="alice-pw-1234")
    resp = client.get("/settings/")
    body = resp.content.decode()
    rows = body.count('data-test="service-row"')
    # 1 existing + 11 blank = 12.
    assert rows == 12, (
        f"User with 1 existing service should see 12 total rows (1 existing + 11 blank). Got {rows}."
    )
