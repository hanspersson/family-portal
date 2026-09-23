"""Password hashing.

Uses the ``bcrypt`` package directly. This used to go through
``passlib``, but passlib is unmaintained and breaks against bcrypt >= 4.1
(its backend self-test hashes a >72-byte password, which bcrypt 5 rejects
with a ValueError). Hashes are standard ``$2b$`` strings either way, so
any hashes created under passlib still verify here.

Login sessions themselves are handled by Flask's built-in ``session``
object, which is a signed (not encrypted) cookie keyed off
``app.config["SECRET_KEY"]`` -- no separate cookie-signing code needed.
"""

from __future__ import annotations

import bcrypt

# bcrypt only ever looks at the first 72 bytes of a password. Older
# versions truncated silently; bcrypt 5 raises instead. Truncating
# explicitly (in both hash and verify) keeps the old behaviour, so a very
# long passphrase still works rather than crashing the login form.
_BCRYPT_MAX_BYTES = 72


def _encode(plain_password: str) -> bytes:
    return plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(_encode(plain_password), bcrypt.gensalt()).decode("ascii")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_encode(plain_password), password_hash.encode("ascii"))
    except ValueError:
        # Malformed/non-bcrypt hash in the DB: treat as a failed login
        # rather than a 500.
        return False
