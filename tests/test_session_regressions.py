"""Tight, named regression tests for bugs we hit and fixed during build-out.

Each test pins a specific past failure mode so a future refactor that brings
back the same bug fails the suite with a clear pointer to the original symptom.
"""
import time

import pytest
from django.contrib.auth import authenticate, get_user_model
from django.core import signing

from apps.security.honeypot import (TIMESTAMP_MAX_AGE, TIMESTAMP_MIN_AGE,
                                    TIMESTAMP_SALT, validate_timestamp)
from apps.users.client_hash import derive_client_hash
from apps.users.hashers import PepperedPBKDF2Hasher

User = get_user_model()


# =========================================================================
# REGRESSION 1 — PepperedPBKDF2Hasher.verify() must NOT pepper twice.
#
# Original bug: verify() applied HMAC pepper to `password` AND then delegated
# to super().verify, which calls self.encode (also peppered) — so the wire
# value was peppered twice on verify and once on encode, producing a
# mismatch. Symptom: every login attempt failed even with the right password.
# =========================================================================

def test_hasher_encode_verify_round_trip_no_double_pepper():
    """The most direct check: encode + verify with the same password must round-trip."""
    h = PepperedPBKDF2Hasher()
    encoded = h.encode("the-password", "the-salt")
    assert h.verify("the-password", encoded) is True, (
        "encode/verify round-trip failed — likely the verify() override is "
        "applying the pepper twice (once explicitly, once via self.encode)."
    )
    assert h.verify("wrong-password", encoded) is False


def test_hasher_set_password_check_password_round_trip():
    """The user-facing entry points (User.set_password / check_password)
    are what the login form actually exercises. Round-trip through them
    too — guards against the same double-pepper bug surfacing only via
    the ORM path."""
    user = User(username="hasher", email="hasher@example.com", is_active=True)
    wire_value = derive_client_hash("plaintext-pw", "hasher@example.com")
    user.set_password(wire_value)
    assert user.check_password(wire_value) is True
    assert user.check_password(wire_value + "x") is False


@pytest.mark.django_db
def test_authenticate_succeeds_with_client_hashed_password():
    """End-to-end: the authenticate() machinery + EmailAuthBackend +
    PepperedPBKDF2Hasher all chained, mirroring what the login form does."""
    plaintext = "round-trip-pw"
    email = "rt@example.com"
    user = User(username="rt", email=email, is_active=True)
    user.set_password(derive_client_hash(plaintext, email))
    user.save()
    authed = authenticate(None, email=email, password=derive_client_hash(plaintext, email))
    assert authed is not None
    assert authed.pk == user.pk


# =========================================================================
# REGRESSION 2 — validate_timestamp must reject signed timestamps where the
# encoded value is older than TIMESTAMP_MAX_AGE seconds.
#
# Original bug: validate_timestamp only checked `elapsed < TIMESTAMP_MIN_AGE`
# (the too-fast case). Stale timestamps slipped through because django.signing
# only enforces max_age on the SIGNATURE issue time, not on the encoded
# integer value. Symptom: a bot could replay a signed token with an arbitrarily
# old encoded "issued at" past the 1-day staleness window.
# =========================================================================

def test_validate_timestamp_accepts_recent_value():
    value = signing.dumps(int(time.time()) - (TIMESTAMP_MIN_AGE + 5), salt=TIMESTAMP_SALT)
    validate_timestamp(value)  # no exception


def test_validate_timestamp_rejects_too_fast():
    """The < MIN_AGE check is the original guard; this protects it from regression."""
    value = signing.dumps(int(time.time()), salt=TIMESTAMP_SALT)
    with pytest.raises(Exception):
        validate_timestamp(value)


def test_validate_timestamp_rejects_stale_encoded_value():
    """The > MAX_AGE check on the encoded value is the bug fix from this session."""
    stale_offset = TIMESTAMP_MAX_AGE + 100
    value = signing.dumps(int(time.time()) - stale_offset, salt=TIMESTAMP_SALT)
    with pytest.raises(Exception):
        validate_timestamp(value)


def test_validate_timestamp_rejects_garbage():
    with pytest.raises(Exception):
        validate_timestamp("not-a-real-signed-value")


# =========================================================================
# REGRESSION 3 — `make_provider_service_formset` must allow up to 12
# blank rows when the profile has no existing services.
#
# Original bug: extra=0 was hard-coded in the formset factory, so a fresh
# user opened /settings/ to a service section with zero rows and no UI
# affordance to add any. Symptom: "I can't modify the services I offer at all.
# It's just an empty box."
# =========================================================================

@pytest.mark.django_db
def test_settings_formset_allows_filling_twelve_services_in_one_save(
    client, make_user, login_client,
):
    """The 12-row cap is the spec maximum; the form must let users hit it
    in a single save without saving + reloading 12 times."""
    from apps.directory.models import ServiceCategory

    make_user()
    login_client()
    cats = list(ServiceCategory.objects.filter(is_active=True))
    assert cats, "seed migration left no categories"
    other = next(c for c in cats if c.is_other_freetext)
    non_other = [c for c in cats if not c.is_other_freetext]

    # Build 12 rows: cycle non-Other categories, plus extra "Other" rows
    # with distinct descriptions (Other has no per-profile uniqueness constraint).
    rows = []
    seen_non_other = set()
    for c in non_other:
        if c.id in seen_non_other:
            continue
        rows.append((c.id, ""))
        seen_non_other.add(c.id)
        if len(rows) >= 12:
            break
    while len(rows) < 12:
        rows.append((other.id, f"Custom service {len(rows) + 1}"))

    payload = {
        "first_name": "Alice", "last_name": "",
        "bio": "A community member offering thoughtful conversation today.",
        "scheduling_url": "https://calendly.com/me",
        "feedback_url": "",
        "providerservice_set-TOTAL_FORMS": "12",
        "providerservice_set-INITIAL_FORMS": "0",
        "providerservice_set-MIN_NUM_FORMS": "0",
        "providerservice_set-MAX_NUM_FORMS": "12",
    }
    for i, (cat_id, desc) in enumerate(rows):
        payload[f"providerservice_set-{i}-id"] = ""
        payload[f"providerservice_set-{i}-profile"] = ""
        payload[f"providerservice_set-{i}-category"] = str(cat_id)
        payload[f"providerservice_set-{i}-custom_description"] = desc
    resp = client.post("/settings/", payload)
    assert resp.status_code == 302, resp.content.decode()[:1500]
    user = User.objects.get(email="alice@example.com")
    assert user.profile.providerservice_set.count() == 12


# =========================================================================
# REGRESSION 4 — `0003_prune_orphan_categories` must remove categories
# whose slug is no longer in the canonical seed list AND ensure the
# canonical list is fully present.
#
# Original bug: editing 0002_seed_categories' CATEGORIES list after the
# migration had already been applied left the old slugs in the DB
# indefinitely (Django runs each migration once). Symptom: user edited
# the seed file, ran migrate, and the old categories were still in the
# directory dropdown.
# =========================================================================

@pytest.mark.django_db
def test_prune_logic_removes_orphans():
    """The prune function (extracted module-level for testability) deletes
    every category not in KEEP_SLUGS plus its provider services, and re-applies
    the canonical list."""
    from importlib import import_module

    from apps.directory.models import ProviderService, ServiceCategory

    # Inject a fake orphan category to simulate the post-rename state.
    orphan = ServiceCategory.objects.create(
        slug="legacy-mentoring", name="Legacy Mentoring", sort_order=999, is_other_freetext=False, is_active=True,
    )
    user = User(username="prune", email="prune@example.com", is_active=True)
    user.set_password("x")
    user.save()
    ProviderService.objects.create(profile=user.profile, category=orphan)
    assert ServiceCategory.objects.filter(slug="legacy-mentoring").exists()

    module = import_module("apps.directory.migrations.0003_prune_orphan_categories")
    module.prune(_FakeAppRegistry(), None)

    assert not ServiceCategory.objects.filter(slug="legacy-mentoring").exists(), (
        "prune migration didn't remove the orphan ServiceCategory"
    )
    assert not ProviderService.objects.filter(category_id=orphan.id).exists(), (
        "prune migration didn't cascade-delete provider services pointing at orphans"
    )
    canonical = {"arabic-language", "mock-interview", "quran-revising", "other"}
    actual = set(ServiceCategory.objects.values_list("slug", flat=True))
    assert canonical <= actual, (
        f"canonical categories missing after prune: {canonical - actual}"
    )


@pytest.mark.django_db
def test_canonical_categories_exactly_match_seed_list():
    """No category exists outside the canonical four. Catches a future drift
    where someone adds a category in 0004+ but forgets to update both 0002
    AND 0003 (the source-of-truth pair)."""
    from apps.directory.models import ServiceCategory

    canonical = {"arabic-language", "mock-interview", "quran-revising", "other"}
    actual = set(ServiceCategory.objects.values_list("slug", flat=True))
    extras = actual - canonical
    assert not extras, (
        f"unexpected categories in DB after migrations: {extras} — "
        f"either edit the canonical list or run the prune migration"
    )


# =========================================================================
# REGRESSION 5 — Django auto-escape of apostrophes in messages.
#
# Original symptom (test-side bug, not a code bug): the smoke test asserted
# the rendered body contained the literal string "We don't recognize…"
# while the rendered HTML had `&#x27;` for the apostrophe. The brittle
# substring match was the bug. This test pins the documented behavior so
# future tests don't regress to fragile literal-apostrophe assertions.
# =========================================================================

@pytest.mark.django_db
def test_warning_message_renders_with_html_escaped_apostrophe(
    client, make_user, login_client,
):
    make_user()
    login_client()
    payload = {
        "first_name": "Alice", "last_name": "",
        "bio": "A community member offering thoughtful conversation today.",
        "scheduling_url": "https://my-tool.example.com/path",
        "feedback_url": "",
        "providerservice_set-TOTAL_FORMS": "0",
        "providerservice_set-INITIAL_FORMS": "0",
        "providerservice_set-MIN_NUM_FORMS": "0",
        "providerservice_set-MAX_NUM_FORMS": "12",
    }
    resp = client.post("/settings/", payload, follow=True)
    body = resp.content.decode()
    # The warning copy is rendered into the page through Django's auto-escape,
    # so the apostrophe becomes &#x27; — assert by the apostrophe-free
    # substring AND verify the exact escaped form is present.
    assert "recognize this scheduling tool" in body
    assert "&#x27;" in body or "&#39;" in body, (
        "warning text should render through Django's auto-escape"
    )


class _FakeAppRegistry:
    """Stand-in for Django's `apps` argument inside a data migration so we
    can call `prune(apps, schema_editor)` with the live ORM."""

    def get_model(self, app_label, model_name):
        from apps.directory.models import (Profile, ProviderService,
                                           ServiceCategory)
        return {
            "ServiceCategory": ServiceCategory,
            "ProviderService": ProviderService,
            "Profile": Profile,
        }[model_name]
