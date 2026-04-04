"""Channel model - represents a YouTube channel configuration."""

from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vidmation.models.base import Base, TimestampMixin, UUIDMixin


class Channel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "channels"

    name: Mapped[str] = mapped_column(String(255))
    youtube_channel_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_path: Mapped[str] = mapped_column(String(500), default="channel_profiles/default.yml")
    oauth_token_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    videos: Mapped[list["Video"]] = relationship(back_populates="channel")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Channel {self.name} ({self.id[:8]})>"
