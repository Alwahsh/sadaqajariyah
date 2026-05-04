"""Spec §4.5 / §4.6 — scheduling_url and feedback_url validation."""
import pytest
from django.core.exceptions import ValidationError

from apps.directory.validators import is_known_scheduling_host, validate_outbound_https_url


@pytest.mark.parametrize("url", [
    "javascript:alert(1)",
    "JavaScript:alert(1)",
    "data:text/html,<script>",
    "file:///etc/passwd",
    "http://example.com/",
    "ftp://example.com/",
    "https://127.0.0.1/",
    "https://[::1]/",
    "https:///nohost",
])
def test_validate_outbound_https_url_rejects(url):
    with pytest.raises(ValidationError):
        validate_outbound_https_url(url)


@pytest.mark.parametrize("url", [
    "https://calendly.com/me/30min",
    "https://cal.com/me",
    "https://savvycal.com/me",
    "https://my-tool.example.com/",
    "https://forms.google.com/abc",
])
def test_validate_outbound_https_url_accepts(url):
    validate_outbound_https_url(url)  # no exception


def test_validate_outbound_https_url_rejects_long_url():
    with pytest.raises(ValidationError):
        validate_outbound_https_url("https://example.com/" + "x" * 600)


@pytest.mark.parametrize("url", [
    "https://calendly.com/me/30min",
    "https://team.calendly.com/me/30min",
    "https://cal.com/me",
    "https://savvycal.com/me",
    "https://calendar.google.com/abc",
    "https://calendar.app.google/abc",
    "https://www.calendly.com/me",  # leading www stripped
])
def test_known_scheduling_host_true(url):
    assert is_known_scheduling_host(url) is True


@pytest.mark.parametrize("url", [
    "https://my-tool.example.com/",
    "https://evil-calendly.com/",  # bare-suffix trick must NOT match
    "https://calendly.com.attacker.test/",
    "",
])
def test_known_scheduling_host_false(url):
    assert is_known_scheduling_host(url) is False
