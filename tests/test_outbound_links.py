"""Spec §11 — outbound link safety attributes on user-supplied URLs."""
import re

import pytest


@pytest.mark.django_db
def test_scheduling_link_has_three_attrs(client, make_profile_with_scheduling):
    p = make_profile_with_scheduling(username="alice", scheduling_url="https://calendly.com/me")
    resp = client.get("/p/alice/")
    body = resp.content.decode()
    # Find the schedule cta href and check the surrounding attrs.
    m = re.search(r'data-test="schedule-cta"[^>]*', body)
    assert m, "schedule-cta not found"
    tag = m.group(0)
    # Get the entire <a> tag including all attributes.
    href_match = re.search(r'href="https://calendly.com/me"[^>]*', body)
    assert href_match
    full_tag = href_match.group(0)
    assert 'target="_blank"' in body
    # Ensure all three appear together on the schedule anchor.
    a_match = re.search(r'<a[^>]+data-test="schedule-cta"[^>]*>', body)
    if not a_match:
        a_match = re.search(r'<a[^>]+href="https://calendly.com/me"[^>]*>', body)
    assert a_match
    a_tag = a_match.group(0)
    assert 'target="_blank"' in a_tag
    assert 'rel="noopener noreferrer"' in a_tag
    assert 'referrerpolicy="no-referrer"' in a_tag


@pytest.mark.django_db
def test_feedback_link_has_three_attrs(client, make_profile_with_scheduling):
    make_profile_with_scheduling(username="alice", feedback_url="https://forms.example.com/abc")
    resp = client.get("/p/alice/")
    body = resp.content.decode()
    a_match = re.search(r'<a[^>]+href="https://forms.example.com/abc"[^>]*>', body)
    assert a_match
    a_tag = a_match.group(0)
    assert 'target="_blank"' in a_tag
    assert 'rel="noopener noreferrer"' in a_tag
    assert 'referrerpolicy="no-referrer"' in a_tag
