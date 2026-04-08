"""User model for authentication and authorization."""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vidmation.models.base import Base, TimestampMixin, UUIDMixin


class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"


class User(Base, UUIDMixin, TimestampMixin):
    """Application user with authentication credentials."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(320), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), default="")

    # Status flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Stripe / Subscription
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier), default=SubscriptionTier.FREE, nullable=False
    )
    subscription_status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )
    subscription_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Usage tracking
    videos_generated_this_month: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    monthly_video_limit: Mapped[int] = mapped_column(
        Integer, default=3, nullable=False  # free tier default
    )

    # Tracking
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Email verification token (stored hashed)
    email_verification_token: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )

    # Password reset token (stored hashed)
    password_reset_token: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    password_reset_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Refresh token hash — one active refresh token per user for simplicity.
    # For multi-device support, move to a separate RefreshToken table.
    refresh_token_hash: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )

    # Google OAuth (stub for later)
    google_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    channels: Mapped[list["Channel"]] = relationship(back_populates="owner")  # noqa: F821
    videos: Mapped[list["Video"]] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return f"<User {self.email!r} ({self.id[:8]})>"

    @property
    def is_subscription_active(self) -> bool:
        """Check if the user has an active paid subscription."""
        if self.subscription_tier == SubscriptionTier.FREE:
            return True  # free tier never expires
        if self.subscription_expires_at is None:
            return False
        return self.subscription_expires_at > datetime.now(timezone.utc)
