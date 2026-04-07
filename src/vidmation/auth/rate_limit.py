"""In-memory rate limiter for auth endpoints.

Uses a sliding-window counter keyed by IP address. For production at scale,
swap this for a Redis-backed implementation.
"""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    """Per-key sliding-window rate limiter (in-memory)."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._windows: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        """Return True if the request is within the rate limit."""
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            timestamps = self._windows[key]
            self._windows[key] = [t for t in timestamps if t > cutoff]
            if len(self._windows[key]) >= limit:
                return False
            self._windows[key].append(now)
            return True


# Singleton limiter for auth endpoints
_auth_limiter = SlidingWindowRateLimiter()

# Separate, stricter limiter for sensitive operations (login, signup, forgot-password)
AUTH_RATE_LIMIT = 10  # requests per window
AUTH_RATE_WINDOW = 60  # seconds

# Even stricter for password reset / forgot password
SENSITIVE_RATE_LIMIT = 5
SENSITIVE_RATE_WINDOW = 300  # 5 minutes


def _get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For behind a reverse proxy."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take the first (leftmost) IP — the original client
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def check_auth_rate_limit(request: Request) -> None:
    """Check the auth rate limit for the current request. Raises 429 on excess."""
    ip = _get_client_ip(request)
    key = f"auth:{ip}"
    if not _auth_limiter.check(key, AUTH_RATE_LIMIT, AUTH_RATE_WINDOW):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication requests. Please try again later.",
            headers={"Retry-After": str(AUTH_RATE_WINDOW)},
        )


def check_sensitive_rate_limit(request: Request) -> None:
    """Stricter rate limit for password reset and similar sensitive ops."""
    ip = _get_client_ip(request)
    key = f"sensitive:{ip}"
    if not _auth_limiter.check(key, SENSITIVE_RATE_LIMIT, SENSITIVE_RATE_WINDOW):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(SENSITIVE_RATE_WINDOW)},
        )
