"""Plan definitions and usage-limit helpers."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from aividio.db.engine import get_session
from aividio.models.user import SubscriptionTier, User

logger = logging.getLogger(__name__)

# ── Plan catalogue ────────────────────────────────────────────────────────

PLANS: dict[str, dict] = {
    "free": {
        "videos_per_month": 3,
        "max_duration_min": 5,
        "resolution": "1080p",
        "watermark": True,
        "price_monthly": 0,
        "price_annual": 0,
    },
    "pro": {
        "videos_per_month": 30,
        "max_duration_min": 30,
        "resolution": "1080p",
        "watermark": False,
        "price_monthly": 29,
        "price_annual": 290,
    },
    "business": {
        "videos_per_month": 100,
        "max_duration_min": 60,
        "resolution": "4K",
        "watermark": False,
        "price_monthly": 79,
        "price_annual": 790,
    },
}

# Map tier enum values to the plan keys above (they match, but be explicit)
_TIER_TO_PLAN: dict[str, str] = {
    SubscriptionTier.FREE.value: "free",
    SubscriptionTier.PRO.value: "pro",
    SubscriptionTier.BUSINESS.value: "business",
}


def get_plan(tier: str) -> dict:
    """Return the plan definition for the given tier name.

    Raises ``KeyError`` if the tier is unknown.
    """
    key = tier.lower()
    if key not in PLANS:
        raise KeyError(f"Unknown plan tier: {tier!r}")
    return PLANS[key]


def _load_user(user_id: str, db: Session | None = None) -> tuple[User, Session, bool]:
    """Load a user by ID.  If *db* is None, open a new session (caller must close)."""
    owns_session = db is None
    if owns_session:
        db = get_session()
    user = db.get(User, user_id)
    if user is None:
        if owns_session:
            db.close()
        raise ValueError(f"User {user_id!r} not found")
    return user, db, owns_session


def check_video_limit(user_id: str, db: Session | None = None) -> bool:
    """Return ``True`` if the user can still generate a video this month."""
    user, db, owns = _load_user(user_id, db)
    try:
        plan = get_plan(user.subscription_tier.value)
        can_generate = user.videos_generated_this_month < plan["videos_per_month"]
        return can_generate
    finally:
        if owns:
            db.close()


def increment_usage(user_id: str, db: Session | None = None) -> None:
    """Increment the user's monthly video generation counter."""
    user, db, owns = _load_user(user_id, db)
    try:
        user.videos_generated_this_month += 1
        db.commit()
        logger.info(
            "User %s usage incremented to %d/%d",
            user_id[:8],
            user.videos_generated_this_month,
            user.monthly_video_limit,
        )
    except Exception:
        db.rollback()
        raise
    finally:
        if owns:
            db.close()
