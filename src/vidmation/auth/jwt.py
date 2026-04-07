"""JWT token creation and verification."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from vidmation.config.settings import get_settings

logger = logging.getLogger(__name__)

JWT_ALGORITHM = "HS256"

# Token type constants embedded in the payload to prevent token confusion attacks.
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


def _get_secret() -> str:
    """Retrieve the JWT signing secret from settings."""
    settings = get_settings()
    return settings.jwt_secret.get_secret_value()


def create_access_token(user_id: str, email: str) -> str:
    """Create a short-lived access token.

    Payload includes:
        sub  — user ID
        email — user email (convenience claim)
        type — "access"
        exp  — expiry timestamp
        iat  — issued-at timestamp
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "type": TOKEN_TYPE_ACCESS,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, _get_secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """Create a long-lived refresh token.

    Payload includes:
        sub  — user ID
        type — "refresh"
        exp  — expiry timestamp
        iat  — issued-at timestamp
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.jwt_refresh_token_expire_days)

    payload: dict[str, Any] = {
        "sub": user_id,
        "type": TOKEN_TYPE_REFRESH,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, _get_secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token.

    Returns the decoded payload dict on success.

    Raises:
        jwt.ExpiredSignatureError: Token has expired.
        jwt.InvalidTokenError: Token is malformed or signature is invalid.
    """
    return jwt.decode(
        token,
        _get_secret(),
        algorithms=[JWT_ALGORITHM],
        options={"require": ["sub", "type", "exp", "iat"]},
    )
