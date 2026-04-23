"""API key authentication and management for programmatic access."""

from __future__ import annotations

import hashlib
import logging
import secrets
import time
from collections import defaultdict
from datetime import datetime, timezone
from threading import Lock

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.orm import Session

from aividio.db.engine import get_session
from aividio.models.api_key import APIKey

logger = logging.getLogger(__name__)

# Header scheme for OpenAPI docs
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# ---------------------------------------------------------------------------
# In-memory rate limiter (per-process; swap for Redis in production at scale)
# ---------------------------------------------------------------------------

class _SlidingWindowCounter:
    """Simple per-key sliding-window rate limiter."""

    def __init__(self) -> None:
        self._lock = Lock()
        # key_hash -> list of request timestamps
        self._windows: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key_hash: str, limit: int, window_seconds: int = 60) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            timestamps = self._windows[key_hash]
            # Prune expired entries
            self._windows[key_hash] = [t for t in timestamps if t > cutoff]
            if len(self._windows[key_hash]) >= limit:
                return False
            self._windows[key_hash].append(now)
            return True


_rate_limiter = _SlidingWindowCounter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash_key(raw_key: str) -> str:
    """SHA-256 hash of a raw API key."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _generate_raw_key() -> str:
    """Generate a cryptographically random API key with a `vm_` prefix."""
    return f"vm_{secrets.token_urlsafe(40)}"


# ---------------------------------------------------------------------------
# API Key Manager
# ---------------------------------------------------------------------------

class APIKeyManager:
    """Manage API keys for programmatic access.

    Keys are stored hashed in the database.  The raw key is returned exactly
    once at creation time.
    """

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    @property
    def session(self) -> Session:
        if self._session is None:
            self._session = get_session()
        return self._session

    # -- CRUD ---------------------------------------------------------------

    def create(self, name: str, rate_limit_per_minute: int = 60) -> tuple[APIKey, str]:
        """Create a new API key.

        Returns:
            A tuple of ``(APIKey record, raw_key_string)``.
        """
        raw_key = _generate_raw_key()
        key_hash = _hash_key(raw_key)
        prefix = raw_key[:8]

        api_key = APIKey(
            name=name,
            key_hash=key_hash,
            prefix=prefix,
            rate_limit_per_minute=rate_limit_per_minute,
        )
        self.session.add(api_key)
        self.session.commit()
        self.session.refresh(api_key)
        logger.info("Created API key '%s' (%s...)", name, prefix)
        return api_key, raw_key

    def validate(self, raw_key: str) -> APIKey | None:
        """Validate a raw API key and return the record if valid and active."""
        key_hash = _hash_key(raw_key)
        stmt = select(APIKey).where(
            APIKey.key_hash == key_hash,
            APIKey.is_active.is_(True),
        )
        api_key = self.session.scalars(stmt).first()
        if api_key is not None:
            api_key.last_used_at = datetime.now(timezone.utc)
            self.session.commit()
        return api_key

    def revoke(self, key_id: str) -> bool:
        """Deactivate an API key by ID."""
        api_key = self.session.get(APIKey, key_id)
        if api_key is None:
            return False
        api_key.is_active = False
        self.session.commit()
        logger.info("Revoked API key '%s' (%s)", api_key.name, api_key.prefix)
        return True

    def list_all(self, active_only: bool = True) -> list[APIKey]:
        """List API keys."""
        stmt = select(APIKey).order_by(APIKey.created_at.desc())
        if active_only:
            stmt = stmt.where(APIKey.is_active.is_(True))
        return list(self.session.scalars(stmt).all())

    def get(self, key_id: str) -> APIKey | None:
        return self.session.get(APIKey, key_id)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def require_api_key(
    request: Request,
    api_key_header: str | None = Security(_api_key_header),
) -> str:
    """FastAPI dependency that validates the ``X-API-Key`` header.

    Returns the API key ID on success.  Raises 401/403/429 on failure.
    """
    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )

    session = get_session()
    try:
        mgr = APIKeyManager(session)
        api_key = mgr.validate(api_key_header)

        if api_key is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or revoked API key",
            )

        # Rate-limit check
        if not _rate_limiter.is_allowed(api_key.key_hash, api_key.rate_limit_per_minute):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded ({api_key.rate_limit_per_minute} req/min)",
                headers={"Retry-After": "60"},
            )

        # Attach key info to request state for downstream use
        request.state.api_key_id = api_key.id
        request.state.api_key_name = api_key.name

        return api_key.id

    finally:
        session.close()
