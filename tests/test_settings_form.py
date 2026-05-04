"""Regression: the /settings/ page must render an editable services formset
with the seeded categories. Past bug: extra=0 on the formset gave fresh users
zero blank rows and no way to add services from the UI.
"""
import re

import pytest

from apps.directory.models import ServiceCategory


@pytest.mark.django_db
def test_settings_renders_one_blank_row_for_new_user(client, make_user, login_client):
    """A fresh user sees a single blank service row. Additional rows are added
    on demand via the Add Another Service button (JS-driven)."""
    make_user()
    login_client()
    resp = client.get("/settings/")
    body = resp.content.decode()
    # Don't count the empty-form template — only initial server-rendered rows.
    body_without_template = _strip_template(body)
    rows = body_without_template.count('data-test="service-row"')
    assert rows == 1, (
        f"Fresh users must see exactly 1 blank service row to start. Got {rows}."
    )


@pytest.mark.django_db
def test_settings_renders_only_existing_rows_for_returning_user(
    client, make_profile_with_scheduling, login_client,
):
    """Returning users see exactly their saved services rendered — no
    pre-emptive blank rows. They use Add Another to grow."""
    from apps.directory.models import ProviderService
    p = make_profile_with_scheduling(username="alice")
    cats = list(ServiceCategory.objects.filter(is_active=True, is_other_freetext=False)[:2])
    for c in cats:
        ProviderService.objects.create(profile=p, category=c)
    login_client(email="alice@example.com", plaintext="alice-pw-1234")
    resp = client.get("/settings/")
    body = resp.content.decode()
    body_without_template = _strip_template(body)
    rows = body_without_template.count('data-test="service-row"')
    assert rows == 2, (
        f"Returning user with 2 saved services should see exactly 2 rows. Got {rows}."
    )


@pytest.mark.django_db
def test_settings_renders_add_another_button(client, make_user, login_client):
    """The Add Another button is the only way to grow the formset — must always
    render on /settings/."""
    make_user()
    login_client()
    resp = client.get("/settings/")
    body = resp.content.decode()
    assert 'data-test="service-add"' in body, (
        "settings page is missing the Add Another Service button"
    )
    assert "Add another service" in body


@pytest.mark.django_db
def test_settings_renders_remove_button_per_row(client, make_user, login_client):
    """Each service row carries its own Remove button — no orphan rows."""
    make_user()
    login_client()
    resp = client.get("/settings/")
    body = resp.content.decode()
    body_without_template = _strip_template(body)
    rows = body_without_template.count('data-test="service-row"')
    removes = body_without_template.count('data-test="service-remove"')
    assert rows == removes, (
        f"every service row must carry its own remove button; rows={rows} removes={removes}"
    )


@pytest.mark.django_db
def test_settings_includes_empty_form_template(client, make_user, login_client):
    """The <template> element with the blank form is what JS clones on Add.
    Without it, the Add button is inert."""
    make_user()
    login_client()
    resp = client.get("/settings/")
    body = resp.content.decode()
    assert "<template" in body
    assert "data-formset-empty" in body
    assert "__prefix__" in body, (
        "empty-form template must contain Django's __prefix__ placeholder for JS to substitute"
    )


@pytest.mark.django_db
def test_settings_loads_formset_js(client, make_user, login_client):
    """The dynamic add/remove logic lives in static/formset.js — must be loaded
    on /settings/ for the Add and Remove buttons to do anything."""
    make_user()
    login_client()
    resp = client.get("/settings/")
    body = resp.content.decode()
    assert "formset.js" in body, "settings page must load static/formset.js"


@pytest.mark.django_db
def test_settings_no_visible_remove_checkbox_for_existing_rows(
    client, make_profile_with_scheduling, login_client,
):
    """Original UX bug we're fixing: a checkbox labelled "Remove" sat next to
    every row. It must be replaced with a hidden input + button."""
    from apps.directory.models import ProviderService
    p = make_profile_with_scheduling(username="alice")
    cat = ServiceCategory.objects.get(slug="mock-interview")
    ProviderService.objects.create(profile=p, category=cat)
    login_client(email="alice@example.com", plaintext="alice-pw-1234")
    resp = client.get("/settings/")
    body = resp.content.decode()
    # The DELETE field must be a hidden input (rendered by us), NOT a checkbox.
    import re
    delete_inputs = re.findall(
        r'<input[^>]+name="providerservice_set-\d+-DELETE"[^>]*>', body,
    )
    assert delete_inputs, "DELETE field must be present for the JS to toggle"
    for tag in delete_inputs:
        assert 'type="hidden"' in tag, (
            f"DELETE input must be type=hidden, got: {tag}"
        )
    # And no visible "Remove" checkbox label adjacent to rows.
    assert 'type="checkbox"' not in body or "DELETE" not in body, (
        "old DELETE-checkbox UX must not be rendered"
    )


@pytest.mark.django_db
def test_save_with_remove_marker_actually_deletes_row(
    client, make_profile_with_scheduling, login_client,
):
    """End-to-end: submitting with DELETE=1 on a row removes it from the DB.
    Catches a regression where the JS toggle stops syncing with formset
    semantics."""
    from apps.directory.models import ProviderService
    p = make_profile_with_scheduling(username="alice")
    cat1 = ServiceCategory.objects.get(slug="mock-interview")
    cat2 = ServiceCategory.objects.get(slug="quran-revising")
    s1 = ProviderService.objects.create(profile=p, category=cat1, custom_description="keep")
    s2 = ProviderService.objects.create(profile=p, category=cat2, custom_description="drop")
    login_client(email="alice@example.com", plaintext="alice-pw-1234")
    payload = {
        "first_name": "Alice", "last_name": "",
        "bio": "A community member offering thoughtful conversation today.",
        "scheduling_url": "https://calendly.com/me",
        "feedback_url": "",
        "providerservice_set-TOTAL_FORMS": "2",
        "providerservice_set-INITIAL_FORMS": "2",
        "providerservice_set-MIN_NUM_FORMS": "0",
        "providerservice_set-MAX_NUM_FORMS": "12",
        "providerservice_set-0-id": str(s1.id),
        "providerservice_set-0-profile": str(p.id),
        "providerservice_set-0-category": str(cat1.id),
        "providerservice_set-0-custom_description": "keep",
        "providerservice_set-0-DELETE": "",
        "providerservice_set-1-id": str(s2.id),
        "providerservice_set-1-profile": str(p.id),
        "providerservice_set-1-category": str(cat2.id),
        "providerservice_set-1-custom_description": "drop",
        "providerservice_set-1-DELETE": "1",
    }
    resp = client.post("/settings/", payload)
    assert resp.status_code == 302
    p.refresh_from_db()
    remaining = list(p.providerservice_set.values_list("custom_description", flat=True))
    assert remaining == ["keep"], (
        f"DELETE=1 row should have been removed. Remaining: {remaining}"
    )


def _strip_template(body):
    """Remove <template>...</template> contents from a rendered body so row counts
    don't double-count the empty-form template."""
    import re
    return re.sub(r"<template[^>]*>.*?</template>", "", body, flags=re.DOTALL)


@pytest.mark.django_db
def test_formset_js_file_exists():
    """static/formset.js must exist and implement the load-bearing helpers."""
    from pathlib import Path
    from django.conf import settings
    js_path = Path(settings.BASE_DIR, "static", "formset.js")
    assert js_path.exists(), "static/formset.js missing"
    text = js_path.read_text()
    assert "data-formset-row" in text
    assert "data-formset-add" in text
    assert "data-formset-remove" in text
    assert "data-formset-empty" in text
    assert "TOTAL_FORMS" in text
    assert "__prefix__" in text


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


