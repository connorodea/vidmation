"""APIKey model - stores hashed API keys for programmatic access."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from aividio.models.base import Base, TimestampMixin, UUIDMixin


class APIKey(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "api_keys"

    name: Mapped[str] = mapped_column(String(255), doc="Human-readable label for this key")
    key_hash: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, doc="SHA-256 hash of the full API key"
    )
    prefix: Mapped[str] = mapped_column(
        String(8), index=True, doc="First 8 chars of key for identification"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=60)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<APIKey {self.name} ({self.prefix}...)>"
