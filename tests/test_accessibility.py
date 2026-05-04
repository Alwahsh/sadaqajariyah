"""Spec §14 — accessibility expectations."""
import pytest


@pytest.mark.django_db
def test_html_lang_en(client):
    resp = client.get("/")
    assert b'<html lang="en">' in resp.content


@pytest.mark.django_db
def test_arabic_wordmark_lang_rtl(client):
    resp = client.get("/")
    body = resp.content.decode()
    assert 'lang="ar"' in body
    assert 'dir="rtl"' in body


@pytest.mark.django_db
def test_skip_link_present(client):
    resp = client.get("/")
    body = resp.content.decode()
    assert 'href="#main"' in body
    assert "Skip to main content" in body


@pytest.mark.django_db
def test_main_id_present(client):
    resp = client.get("/")
    assert b'id="main"' in resp.content


@pytest.mark.django_db
def test_wordmark_aria_label(client):
    resp = client.get("/")
    body = resp.content.decode()
    assert 'aria-label="Sadaqa Jariyah"' in body


@pytest.mark.django_db
def test_avatar_aria_hidden_in_directory(client, make_profile_with_scheduling):
    make_profile_with_scheduling(username="alice", first_name="Alice")
    resp = client.get("/directory/")
    body = resp.content.decode()
    # The avatar block carries aria-hidden.
    assert 'aria-hidden="true"' in body


@pytest.mark.django_db
def test_signup_form_visible_label_for_username(client):
    resp = client.get("/accounts/signup/")
    body = resp.content.decode()
    # Must have an actual <label> for the username field, not just a placeholder.
    assert "<label" in body
    assert "Username" in body
