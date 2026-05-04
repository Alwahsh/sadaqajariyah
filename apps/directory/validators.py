"""URL validation helpers shared between scheduling_url and feedback_url."""
import ipaddress
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError

BAD_SCHEME_PREFIXES = ("javascript:", "data:", "file:")


def validate_outbound_https_url(url):
    """Hard-block validation shared by scheduling_url and feedback_url.

    Rejects:
      - javascript:/data:/file: URIs (case-insensitive)
      - non-https schemes
      - URLs with no host
      - IP-literal hosts (incl. IPv6 in brackets)
      - URLs longer than 500 characters
    """
    if url is None:
        raise ValidationError("Enter a URL.")
    if len(url) > 500:
        raise ValidationError("URL too long (max 500 characters).")

    stripped = url.strip()
    lowered = stripped.lower()
    if any(lowered.startswith(p) for p in BAD_SCHEME_PREFIXES):
        raise ValidationError("Only https URLs are accepted.")

    parsed = urlparse(stripped)
    if parsed.scheme.lower() != "https":
        raise ValidationError("Only https URLs are accepted.")

    host = parsed.hostname
    if not host:
        raise ValidationError("Enter a valid URL with a hostname.")

    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        # If it parsed as an IP, reject — legitimate scheduling/form tools don't publish raw-IP links.
        raise ValidationError("IP-literal hosts are not allowed.")


def is_known_scheduling_host(url):
    """Return True if the URL's host suffix-matches an entry in KNOWN_SCHEDULING_HOSTS
    on a label boundary (so `evil-calendly.com` does NOT match `calendly.com`).
    """
    if not url:
        return False
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    allowlist = getattr(settings, "KNOWN_SCHEDULING_HOSTS", [])
    for allowed in allowlist:
        a = allowed.lower()
        if host == a or host.endswith("." + a):
            return True
    return False
