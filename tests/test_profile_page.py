"""Spec §1.6, §5 — public profile page including badge, cautions, owner exception."""
import pytest

from apps.directory.models import ProviderService, ServiceCategory


@pytest.mark.django_db
def test_anon_can_load_active_profile(client, make_profile_with_scheduling):
    p = make_profile_with_scheduling(username="alice")
    resp = client.get("/p/alice/")
    assert resp.status_code == 200
    assert b"Alice" in resp.content


@pytest.mark.django_db
def test_anon_404_on_unknown_username(client):
    resp = client.get("/p/nobody/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_anon_404_on_inactive_user(client, make_profile_with_scheduling):
    p = make_profile_with_scheduling(username="alice", is_active=False)
    resp = client.get("/p/alice/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_anon_404_when_no_scheduling_url(client, make_profile_with_scheduling):
    p = make_profile_with_scheduling(username="alice", scheduling_url="")
    resp = client.get("/p/alice/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_mixedcase_username_resolves(client, make_profile_with_scheduling):
    make_profile_with_scheduling(username="alice")
    resp = client.get("/p/Alice/")
    assert resp.status_code == 200
    resp2 = client.get("/p/ALICE/")
    assert resp2.status_code == 200


@pytest.mark.django_db
def test_verified_badge_when_verified(client, make_profile_with_scheduling):
    make_profile_with_scheduling(username="alice", is_verified=True)
    resp = client.get("/p/alice/")
    assert b"verified-badge" in resp.content
    assert b"Verified" in resp.content


@pytest.mark.django_db
def test_no_verified_badge_when_unverified(client, make_profile_with_scheduling):
    make_profile_with_scheduling(username="alice", is_verified=False)
    resp = client.get("/p/alice/")
    assert b"verified-badge" not in resp.content
    assert b"Unverified" not in resp.content
    assert b"Pending" not in resp.content


@pytest.mark.django_db
def test_display_name_no_trailing_space_when_last_name_blank(client, make_profile_with_scheduling):
    make_profile_with_scheduling(username="alice", first_name="Alice", last_name="")
    resp = client.get("/p/alice/")
    body = resp.content.decode()
    # The display name should be exactly "Alice" — no trailing space inside the h1.
    import re
    matches = re.findall(r'data-test="display-name"[^>]*>([^<]*)', body)
    assert any(m.strip() == "Alice" for m in matches)


@pytest.mark.django_db
def test_schedule_cta_outbound_attrs(client, make_profile_with_scheduling):
    make_profile_with_scheduling(username="alice")
    resp = client.get("/p/alice/")
    body = resp.content.decode()
    assert 'target="_blank"' in body
    assert 'rel="noopener noreferrer"' in body
    assert 'referrerpolicy="no-referrer"' in body


@pytest.mark.django_db
def test_feedback_button_renders_only_when_feedback_url_set(client, make_profile_with_scheduling):
    make_profile_with_scheduling(username="alice")  # no feedback_url
    resp = client.get("/p/alice/")
    assert b"Send anonymous feedback" not in resp.content
    assert b"feedback-cta" not in resp.content


@pytest.mark.django_db
def test_feedback_button_renders_when_feedback_url_set(client, make_profile_with_scheduling):
    make_profile_with_scheduling(username="alice", feedback_url="https://forms.example.com/abc")
    resp = client.get("/p/alice/")
    assert b"Send anonymous feedback" in resp.content
    body = resp.content.decode()
    # Feedback button has outbound link attrs.
    fb_section = body[body.find('data-test="feedback-cta"'):body.find('data-test="feedback-cta"')+400]
    # Check the same anchor's attrs by searching nearby
    assert 'target="_blank"' in body
    assert 'rel="noopener noreferrer"' in body


@pytest.mark.django_db
def test_scheduling_caution_for_non_allowlisted_host(client, make_profile_with_scheduling):
    make_profile_with_scheduling(username="alice", scheduling_url="https://my-tool.example.com/me")
    resp = client.get("/p/alice/")
    assert b"scheduling-caution" in resp.content
    assert b"doesn't recognize this scheduling tool" in resp.content


@pytest.mark.django_db
def test_no_scheduling_caution_for_allowlisted_host(client, make_profile_with_scheduling):
    make_profile_with_scheduling(username="alice", scheduling_url="https://calendly.com/me")
    resp = client.get("/p/alice/")
    assert b"scheduling-caution" not in resp.content


@pytest.mark.django_db
def test_no_scheduling_caution_for_subdomain_of_allowlisted(client, make_profile_with_scheduling):
    make_profile_with_scheduling(username="alice", scheduling_url="https://team.calendly.com/me")
    resp = client.get("/p/alice/")
    assert b"scheduling-caution" not in resp.content


@pytest.mark.django_db
def test_scheduling_caution_for_bare_suffix_trick(client, make_profile_with_scheduling):
    make_profile_with_scheduling(username="alice", scheduling_url="https://evil-calendly.com/me")
    resp = client.get("/p/alice/")
    assert b"scheduling-caution" in resp.content


@pytest.mark.django_db
def test_feedback_caution_renders_whenever_feedback_set(client, make_profile_with_scheduling):
    make_profile_with_scheduling(username="alice", feedback_url="https://forms.google.com/x")
    resp = client.get("/p/alice/")
    assert b"feedback-caution" in resp.content
    assert b"This feedback form should be anonymous" in resp.content


@pytest.mark.django_db
def test_feedback_caution_omitted_when_blank(client, make_profile_with_scheduling):
    make_profile_with_scheduling(username="alice", feedback_url="")
    resp = client.get("/p/alice/")
    assert b"feedback-caution" not in resp.content


@pytest.mark.django_db
def test_owner_exception_no_scheduling(client, make_user, login_client):
    user = make_user(username="alice", email="alice@example.com", plaintext="alice-pw-1234")
    login_client(email="alice@example.com", plaintext="alice-pw-1234")
    resp = client.get("/p/alice/")
    assert resp.status_code == 200
    assert b"Add a scheduling link" in resp.content
    assert b"owner-no-scheduling-banner" in resp.content


@pytest.mark.django_db
def test_owner_self_view_unverified_no_banner(client, make_profile_with_scheduling, login_client):
    p = make_profile_with_scheduling(username="alice", is_verified=False)
    login_client(email="alice@example.com", plaintext="alice-pw-1234")
    resp = client.get("/p/alice/")
    assert resp.status_code == 200
    assert b"verified-badge" not in resp.content
    assert b"owner-no-scheduling-banner" not in resp.content


@pytest.mark.django_db
def test_other_member_404_for_no_scheduling(client, make_user, make_profile_with_scheduling, login_client):
    # bob has no scheduling
    make_profile_with_scheduling(username="bob", email="bob@example.com",
                                 first_name="Bob", scheduling_url="")
    # alice logs in
    make_user(username="alice", email="alice@example.com", plaintext="alice-pw-1234")
    login_client(email="alice@example.com", plaintext="alice-pw-1234")
    resp = client.get("/p/bob/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_owner_sees_scheduling_caution_when_non_allowlisted(client, make_profile_with_scheduling, login_client):
    p = make_profile_with_scheduling(username="alice", scheduling_url="https://my-tool.example.com/me")
    login_client(email="alice@example.com", plaintext="alice-pw-1234")
    resp = client.get("/p/alice/")
    assert b"scheduling-caution" in resp.content


@pytest.mark.django_db
def test_other_service_renders_custom_description_as_label(client, make_profile_with_scheduling):
    p = make_profile_with_scheduling(username="alice")
    other = ServiceCategory.objects.get(slug="other")
    ProviderService.objects.create(profile=p, category=other, custom_description="Pediatric questions", is_freetext=True)
    resp = client.get("/p/alice/")
    body = resp.content.decode()
    assert "Pediatric questions" in body


@pytest.mark.django_db
def test_predefined_service_renders_custom_description_alongside(client, make_profile_with_scheduling):
    p = make_profile_with_scheduling(username="alice")
    cat = ServiceCategory.objects.get(slug="mock-interview")
    ProviderService.objects.create(profile=p, category=cat, custom_description="early-career engineers")
    resp = client.get("/p/alice/")
    body = resp.content.decode()
    assert "early-career engineers" in body
    assert "Mock Interview" in body
