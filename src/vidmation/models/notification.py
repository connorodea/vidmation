"""Notification model - tracks sent notifications and read state."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from vidmation.models.base import Base, TimestampMixin, UUIDMixin


class Notification(Base, UUIDMixin, TimestampMixin):
    """Persisted notification record.

    Each row represents a single notification event that was dispatched
    through one or more channels (email, discord, slack, in-app).
    """

    __tablename__ = "notifications"

    event: Mapped[str] = mapped_column(
        String(100), index=True, doc="Event type, e.g. 'video_complete', 'job_failed'"
    )
    title: Mapped[str] = mapped_column(String(500), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    data_json: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, doc="Arbitrary payload associated with the event"
    )
    channels_sent: Mapped[list | None] = mapped_column(
        JSON, nullable=True, doc="List of channel names that received this notification"
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, doc="When the user dismissed / read this"
    )

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    @property
    def event_icon(self) -> str:
        """Map event types to icon identifiers for the UI."""
        icons = {
            "video_complete": "film",
            "job_failed": "alert-triangle",
            "upload_complete": "upload-cloud",
            "batch_complete": "layers",
            "cost_alert": "dollar-sign",
            "schedule_fired": "clock",
            "publish_complete": "share-2",
        }
        return icons.get(self.event, "bell")

    def __repr__(self) -> str:
        read_flag = "read" if self.is_read else "unread"
        return f"<Notification [{self.event}] {read_flag} ({self.id[:8]})>"
