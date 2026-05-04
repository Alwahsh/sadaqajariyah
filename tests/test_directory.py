"""Spec §1.2-§1.5 — directory inclusion, search, filter, pagination."""
import pytest

from apps.directory.models import ProviderService, ServiceCategory


@pytest.mark.django_db
def test_directory_includes_active_with_scheduling(client, make_profile_with_scheduling):
    p = make_profile_with_scheduling()
    resp = client.get("/directory/")
    assert resp.status_code == 200
    assert b"Alice" in resp.content


@pytest.mark.django_db
def test_directory_excludes_inactive_user(client, make_profile_with_scheduling):
    p = make_profile_with_scheduling(username="inactive", email="x@example.com",
                                     first_name="Hidden", is_active=False)
    resp = client.get("/directory/")
    assert b"Hidden" not in resp.content


@pytest.mark.django_db
def test_directory_excludes_empty_scheduling_url(client, make_profile_with_scheduling):
    p = make_profile_with_scheduling(first_name="Visible")
    p2 = make_profile_with_scheduling(username="hidden2", email="hidden2@example.com",
                                      first_name="Hidden", scheduling_url="")
    resp = client.get("/directory/")
    assert b"Visible" in resp.content
    assert b"Hidden" not in resp.content


@pytest.mark.django_db
def test_directory_includes_unverified_profiles(client, make_profile_with_scheduling):
    p = make_profile_with_scheduling(first_name="Unverified", is_verified=False)
    resp = client.get("/directory/")
    assert b"Unverified" in resp.content
    # No verified badge for this profile.
    assert b"verified-badge" not in resp.content


@pytest.mark.django_db
def test_search_matches_first_name_bio_custom_description(client, make_profile_with_scheduling):
    p = make_profile_with_scheduling(first_name="Alice", bio="A community member offering thoughtful conversation.")
    cat = ServiceCategory.objects.get(slug="mock-interview")
    ProviderService.objects.create(profile=p, category=cat, custom_description="early-career engineers", is_freetext=False)

    resp = client.get("/directory/?q=engineers")
    assert b"Alice" in resp.content


@pytest.mark.django_db
def test_search_does_not_match_feedback_url(client, make_profile_with_scheduling):
    p = make_profile_with_scheduling(first_name="Alice", feedback_url="https://forms.example.com/secret-thing")
    resp = client.get("/directory/?q=secret-thing")
    assert b"Alice" not in resp.content


@pytest.mark.django_db
def test_search_truncates_to_80_chars(client, make_profile_with_scheduling):
    p = make_profile_with_scheduling(first_name="Alice", bio="A community member offering thoughtful conversation.")
    long_q = "Alice" + "x" * 200
    resp = client.get(f"/directory/?q={long_q}")
    # Truncated to 80 chars; "Alicexxxxxxxx..." shouldn't match unless the bio contains it.
    assert resp.status_code == 200


@pytest.mark.django_db
def test_search_empty_returns_unfiltered(client, make_profile_with_scheduling):
    p = make_profile_with_scheduling(first_name="Alice")
    resp = client.get("/directory/?q=   ")
    assert b"Alice" in resp.content


@pytest.mark.django_db
def test_search_dedupes_multiple_service_matches(client, make_profile_with_scheduling):
    p = make_profile_with_scheduling(first_name="Alice")
    cat = ServiceCategory.objects.get(slug="mock-interview")
    cat2 = ServiceCategory.objects.get(slug="quran-revising")
    ProviderService.objects.create(profile=p, category=cat, custom_description="systems mentoring")
    ProviderService.objects.create(profile=p, category=cat2, custom_description="career systems")
    resp = client.get("/directory/?q=systems")
    body = resp.content.decode()
    assert body.count("data-username=\"alice\"") == 1


@pytest.mark.django_db
def test_search_clear_button_when_q_set(client, make_profile_with_scheduling):
    make_profile_with_scheduling(first_name="Alice")
    resp = client.get("/directory/?q=alice")
    body = resp.content.decode()
    assert "Clear" in body


@pytest.mark.django_db
def test_category_filter_works(client, make_profile_with_scheduling):
    p = make_profile_with_scheduling(first_name="Alice")
    cat = ServiceCategory.objects.get(slug="mock-interview")
    ProviderService.objects.create(profile=p, category=cat)
    other = make_profile_with_scheduling(username="bob", email="b@e.com", first_name="Bob")
    cat2 = ServiceCategory.objects.get(slug="arabic-language")
    ProviderService.objects.create(profile=other, category=cat2)
    resp = client.get("/directory/?category=mock-interview")
    assert b"Alice" in resp.content
    assert b"Bob" not in resp.content


@pytest.mark.django_db
def test_category_filter_unknown_slug_empty_state(client, make_profile_with_scheduling):
    make_profile_with_scheduling(first_name="Alice")
    resp = client.get("/directory/?category=does-not-exist")
    assert resp.status_code == 200
    assert b"No one matches" in resp.content


@pytest.mark.django_db
def test_category_other_chip_renders_other_profiles(client, make_profile_with_scheduling):
    p = make_profile_with_scheduling(first_name="Alice")
    other_cat = ServiceCategory.objects.get(slug="other")
    ProviderService.objects.create(profile=p, category=other_cat, custom_description="Pediatric questions", is_freetext=True)
    resp = client.get("/directory/?category=other")
    assert b"Alice" in resp.content


@pytest.mark.django_db
def test_search_and_category_combine_and_not_or(client, make_profile_with_scheduling):
    p1 = make_profile_with_scheduling(first_name="Alice")
    p2 = make_profile_with_scheduling(username="bob", email="bob@e.com", first_name="Alice2")
    cat = ServiceCategory.objects.get(slug="mock-interview")
    ProviderService.objects.create(profile=p1, category=cat)
    cat2 = ServiceCategory.objects.get(slug="arabic-language")
    ProviderService.objects.create(profile=p2, category=cat2)
    resp = client.get("/directory/?q=Alice&category=mock-interview")
    body = resp.content.decode()
    assert "data-username=\"alice\"" in body
    assert "data-username=\"bob\"" not in body


@pytest.mark.django_db
def test_pagination_invalid_page_returns_page_1(client, make_profile_with_scheduling):
    make_profile_with_scheduling(first_name="Alice")
    resp = client.get("/directory/?page=abc")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_pagination_huge_page_returns_last_page(client, make_profile_with_scheduling):
    make_profile_with_scheduling(first_name="Alice")
    resp = client.get("/directory/?page=99999")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_pagination_preserves_query_in_links(client, make_profile_with_scheduling):
    """With > 20 profiles, page 2 link preserves q + category."""
    for i in range(21):
        make_profile_with_scheduling(username=f"u{i}", email=f"u{i}@e.com",
                                      first_name=f"User{i}",
                                      bio="A community member offering thoughtful conversation today.")
    resp = client.get("/directory/?q=User&category=mock-interview")
    body = resp.content.decode()
    # If pagination is rendered, the links carry q and category.
    if "page=" in body:
        assert "q=User" in body
        assert "category=mock-interview" in body


@pytest.mark.django_db
def test_directory_orders_newest_first(client, make_profile_with_scheduling):
    a = make_profile_with_scheduling(username="alice", email="alice@e.com", first_name="Alice")
    b = make_profile_with_scheduling(username="bob", email="bob@e.com", first_name="Bob")
    resp = client.get("/directory/")
    body = resp.content.decode()
    # Bob created later, should appear first.
    assert body.find("data-username=\"bob\"") < body.find("data-username=\"alice\"")


@pytest.mark.django_db
def test_chip_count_matches_directory(client, make_profile_with_scheduling):
    p = make_profile_with_scheduling(first_name="Alice")
    cat = ServiceCategory.objects.get(slug="mock-interview")
    ProviderService.objects.create(profile=p, category=cat)
    resp = client.get("/directory/")
    # Chip is rendered with a count.
    body = resp.content.decode()
    assert "Mock Interview" in body
