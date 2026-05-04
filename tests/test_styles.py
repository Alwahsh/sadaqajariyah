"""Regression: the templates use Tailwind utility class names; without them
defined in static/styles.css the site renders unstyled. These tests fail if
the stylesheet stops covering the design tokens or the most load-bearing
utility classes used across templates.

Why this is a real regression risk: in v1 we hand-rolled styles.css instead
of running the Tailwind CLI at build time (the plan's Phase 3 build is
production-only). If a future change adds a new template class without
updating styles.css, the page silently looks broken in dev. These tests
catch that by reading styles.css and asserting required selectors are
present.
"""
import re
from pathlib import Path

import pytest

from django.conf import settings


STYLES_PATH = Path(settings.BASE_DIR) / "static" / "styles.css"


def _stylesheet_text() -> str:
    assert STYLES_PATH.exists(), f"static/styles.css is missing at {STYLES_PATH}"
    return STYLES_PATH.read_text()


def test_stylesheet_is_substantial():
    """The stylesheet must have real content — a 1-line stub always fails."""
    text = _stylesheet_text()
    # 5KB threshold lets a sufficiently-detailed hand-roll pass while
    # rejecting the kind of empty stub that ships unstyled to users.
    assert len(text) >= 5_000, (
        f"static/styles.css is only {len(text)} bytes — site would look unstyled. "
        f"Either run the Tailwind CLI build or update the hand-rolled stylesheet."
    )


def test_design_tokens_present():
    """Each Garden palette token must resolve to a hex value somewhere in the file."""
    text = _stylesheet_text()
    required_hexes = [
        "#F5EFE3",  # bg
        "#FBF7EE",  # bgCard
        "#EFE8D8",  # bgSoft
        "#1F2A24",  # ink
        "#5C6660",  # inkSoft
        "#3F5D4A",  # sageDeep (primary CTA)
        "#D9E4D6",  # sageSoft
        "#FBF1D6",  # warning bg
        "#E8D58A",  # warning border
        "#6B5418",  # warning text
    ]
    for hex_value in required_hexes:
        assert hex_value in text or hex_value.lower() in text.lower(), (
            f"design token {hex_value} missing from static/styles.css"
        )


# Class tokens that MUST be defined in the stylesheet for the site to look right.
# These are the load-bearing ones — colors and the layout primitives the templates
# use heavily. Adding more tokens here is fine; removing a token without removing
# its template usage is the regression mode this test catches.
REQUIRED_SELECTORS = [
    # Layout primitives
    ".flex",
    ".grid",
    ".items-center",
    ".justify-between",
    ".gap-3",
    ".mx-auto",
    # Colors
    ".bg-bg",
    ".bg-bgCard",
    ".bg-bgSoft",
    ".bg-sage-deep",
    ".bg-sage-soft",
    ".text-ink",
    ".text-inkSoft",
    ".text-sage-deep",
    ".text-bgCard",
    # Border / radius
    ".border-rule",
    ".border-b",
    ".border-t",
    # Component classes from templates
    ".btn",
    ".btn-primary",
    ".form-input",
    ".live-count",
    ".chip",
    ".chips",
    ".sticky-cta",
    ".banner-warning",
    ".caution-panel",
    ".badge-verified",
    ".empty",
    ".pagination",
    ".honeypot",
    ".sr-only",
    # Custom widths from design notes
    ".max-w-\\[680px\\]",
    ".max-w-\\[980px\\]",
    ".max-w-\\[1080px\\]",
]


@pytest.mark.parametrize("selector", REQUIRED_SELECTORS)
def test_required_selector_defined(selector):
    text = _stylesheet_text()
    # Look for selector at the start of a rule (preceded by whitespace, comma,
    # or beginning of file, and followed by whitespace, comma, brace, or colon).
    pattern = re.compile(r'(^|[\s,])' + re.escape(selector) + r'(?=[\s,:{])', re.MULTILINE)
    assert pattern.search(text), (
        f"selector {selector} missing from static/styles.css — templates that use this "
        f"class will render without the intended treatment"
    )


@pytest.mark.django_db
def test_home_page_links_stylesheet(client):
    """The home page response references the bundled stylesheet."""
    resp = client.get("/")
    body = resp.content.decode()
    assert "/static/styles.css" in body or "styles.css" in body, (
        "home page is not loading static/styles.css"
    )


@pytest.mark.django_db
def test_home_page_links_google_fonts(client):
    """Garden palette typography depends on DM Sans + Fraunces + Noto Naskh Arabic;
    these come from Google Fonts at runtime."""
    resp = client.get("/")
    body = resp.content.decode()
    assert "fonts.googleapis.com" in body, (
        "home page is not loading Google Fonts; the palette typography won't render"
    )


@pytest.mark.django_db
def test_csp_allows_stylesheet_origins(client):
    """CSP must allow the stylesheet origins the templates reference, otherwise the
    browser blocks them and the page renders unstyled even when the file is served."""
    resp = client.get("/")
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "fonts.googleapis.com" in csp, "CSP must allow fonts.googleapis.com (the Google Fonts CSS)"
    assert "fonts.gstatic.com" in csp, "CSP must allow fonts.gstatic.com (the woff2 files)"
    # 'self' covers the local /static/styles.css.
    assert "'self'" in csp, "CSP must allow 'self' so /static/styles.css loads"
