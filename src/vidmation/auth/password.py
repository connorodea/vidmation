"""Password hashing and verification using bcrypt."""

from __future__ import annotations

import bcrypt


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt.

    Uses a cost factor of 12 (bcrypt default), which provides a good balance
    between security and performance (~250ms per hash on modern hardware).
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Returns True if the password matches, False otherwise.
    Uses constant-time comparison internally (bcrypt handles this).
    """
    try:
        password_bytes = password.encode("utf-8")
        hash_bytes = password_hash.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except (ValueError, TypeError):
        # Malformed hash or encoding issue — treat as mismatch
        return False
