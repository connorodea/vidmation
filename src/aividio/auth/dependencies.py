"""FastAPI dependencies for JWT-based authentication."""

from __future__ import annotations

import logging

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from aividio.auth.jwt import TOKEN_TYPE_ACCESS, decode_token
from aividio.db.engine import get_session
from aividio.models.user import User

logger = logging.getLogger(__name__)

# HTTPBearer extracts the token from the "Authorization: Bearer <token>" header.
_bearer_scheme = HTTPBearer(auto_error=True)
_bearer_scheme_optional = HTTPBearer(auto_error=False)


def _get_db() -> Session:
    """Yield a database session, closing it after the request."""
    session = get_session()
    try:
        return session
    except Exception:
        session.close()
        raise


def _resolve_user_from_token(
    token: str,
    db: Session,
    *,
    require: bool = True,
) -> User | None:
    """Decode a JWT access token and load the corresponding User.

    If *require* is True, raises HTTPException on any failure.
    If *require* is False, returns None on failure.
    """
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        if require:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None
    except jwt.InvalidTokenError:
        if require:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None

    # Ensure this is an access token, not a refresh token
    if payload.get("type") != TOKEN_TYPE_ACCESS:
        if require:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None

    user_id = payload.get("sub")
    if not user_id:
        if require:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None

    user = db.get(User, user_id)
    if user is None:
        if require:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None

    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> User:
    """Return the authenticated user from the Bearer token.

    Raises 401 if the token is missing, expired, invalid, or the user
    no longer exists.
    """
    db = _get_db()
    try:
        user = _resolve_user_from_token(credentials.credentials, db, require=True)
        assert user is not None  # _resolve_user_from_token raises if require=True
        return user
    except Exception:
        db.close()
        raise


async def require_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """Ensure the authenticated user has an active account.

    Raises 403 if the user is deactivated.
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )
    return user


async def require_admin(
    user: User = Depends(require_active_user),
) -> User:
    """Ensure the authenticated user is an active admin.

    Raises 403 if the user is not an admin.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


async def optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme_optional),
) -> User | None:
    """Return the authenticated user if a valid token is provided, else None.

    Does not raise on missing or invalid tokens — useful for endpoints that
    behave differently for authenticated vs. anonymous users.
    """
    if credentials is None:
        return None

    db = _get_db()
    try:
        return _resolve_user_from_token(credentials.credentials, db, require=False)
    except Exception:
        db.close()
        return None
