"""Server-side equivalent of apps/users/static/users/auth-hash.js.

PBKDF2-SHA256 of the plaintext password, with the lowercased+trimmed email
as the salt, 100k iterations, 32-byte output, hex-encoded.

The JS module and this helper MUST stay byte-for-byte identical — the
management commands (`create_user`, `reset_password`) call this function so
their stored hashes match what the JS form would produce for the same email
and password.
"""
import hashlib

from django.conf import settings


def derive_client_hash(plaintext: str, email: str) -> str:
    salt = email.strip().lower().encode("utf-8")
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        plaintext.encode("utf-8"),
        salt,
        settings.CLIENT_HASH_ITERATIONS,
        dklen=settings.CLIENT_HASH_DKLEN,
    )
    return digest.hex()


HASH_RE_PATTERN = r"^[a-f0-9]{64}$"
