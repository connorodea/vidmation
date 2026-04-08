"""Channel model - represents a YouTube channel configuration."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vidmation.models.base import Base, TimestampMixin, UUIDMixin


class Channel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "channels"

    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    youtube_channel_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    youtube_channel_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_path: Mapped[str] = mapped_column(String(500), default="channel_profiles/default.yml")
    oauth_token_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    oauth_connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    owner: Mapped["User | None"] = relationship(back_populates="channels")  # noqa: F821
    videos: Mapped[list["Video"]] = relationship(back_populates="channel")  # noqa: F821

    @property
    def is_youtube_connected(self) -> bool:
        """Return True if this channel has a stored OAuth token."""
        return self.oauth_token_json is not None and len(self.oauth_token_json) > 0

    def __repr__(self) -> str:
        return f"<Channel {self.name} ({self.id[:8]})>"
