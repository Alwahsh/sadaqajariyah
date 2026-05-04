"""Spec §1.7, §1.8, §15 — static pages, robots, error templates."""
import pytest
from django.test import override_settings


@pytest.mark.django_db
def test_privacy_loads(client):
    resp = client.get("/privacy/")
    assert resp.status_code == 200
    assert b"Anonymous feedback links" in resp.content
    assert b"What we hold" in resp.content


@pytest.mark.django_db
def test_terms_loads(client):
    resp = client.get("/terms/")
    assert resp.status_code == 200
    assert b"Terms" in resp.content


@pytest.mark.django_db
def test_footer_links_to_privacy_and_terms(client):
    resp = client.get("/")
    body = resp.content.decode()
    assert "/privacy/" in body
    assert "/terms/" in body


@pytest.mark.django_db
def test_admin_returns_404(client):
    resp = client.get("/admin/")
    assert resp.status_code == 404


@override_settings(SITE_IS_PRODUCTION=True)
@pytest.mark.django_db
def test_robots_in_production(client):
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "Allow: /" in body
    assert "Disallow: /accounts/" in body
    assert "Disallow: /settings/" in body
    assert "Allow: /p/" in body
    assert "/admin/" not in body


@pytest.mark.django_db
def test_robots_in_nonproduction(client):
    """When SITE_IS_PRODUCTION is unset, robots.txt is Disallow: /."""
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    assert b"Disallow: /" in resp.content


@pytest.mark.django_db
def test_xrobots_header_in_nonproduction(client):
    resp = client.get("/")
    assert "X-Robots-Tag" in resp.headers
    assert "noindex" in resp.headers["X-Robots-Tag"]


@override_settings(SITE_IS_PRODUCTION=True)
@pytest.mark.django_db
def test_xrobots_header_absent_in_production(client):
    resp = client.get("/")
    assert "X-Robots-Tag" not in resp.headers


@pytest.mark.django_db
def test_404_renders_custom_template(client):
    resp = client.get("/this-url-does-not-exist/")
    assert resp.status_code == 404
    assert b"data-error-page=\"404\"" in resp.content
