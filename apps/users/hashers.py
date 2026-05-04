import hashlib
import hmac

from django.conf import settings
from django.contrib.auth.hashers import PBKDF2PasswordHasher


class PepperedPBKDF2Hasher(PBKDF2PasswordHasher):
    """PBKDF2 with a server-side pepper applied via HMAC-SHA256 before delegating
    to Django's stock PBKDF2 hasher.

    `password` here is whatever the form submitted — for the public forms in v1
    that's a hex-encoded client-side hash; for shell paths (`set_password`) it's
    whatever the operator passes in. The pepper is layered identically for both,
    so a DB compromise leaves an attacker still needing the pepper to crack.
    """

    algorithm = "peppered_pbkdf2_sha256"

    def _pepper(self, password):
        return hmac.new(settings.PEPPER.encode("utf-8"), password.encode("utf-8"), hashlib.sha256).hexdigest()

    def encode(self, password, salt, iterations=None):
        return super().encode(self._pepper(password), salt, iterations)

    def verify(self, password, encoded):
        # super().verify calls self.encode internally, which already peppers.
        # Don't pepper again here — that would double-apply the HMAC.
        return super().verify(password, encoded)

    def safe_summary(self, encoded):
        return super().safe_summary(encoded)
