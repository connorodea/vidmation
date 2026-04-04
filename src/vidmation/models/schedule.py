"""Schedule model - tracks one-time and recurring publish schedules."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vidmation.models.base import Base, TimestampMixin, UUIDMixin


class ScheduleType(str, enum.Enum):
    ONE_TIME = "one_time"
    RECURRING = "recurring"


class ScheduleStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class TopicSource(str, enum.Enum):
    AI = "ai"
    CONTENT_CALENDAR = "content_calendar"
    RSS = "rss"
    MANUAL = "manual"


class Schedule(Base, UUIDMixin, TimestampMixin):
    """A scheduled publish or recurring content-generation entry.

    For ``one_time`` schedules a ``video_id`` is usually present and
    ``publish_at`` is the target time.  For ``recurring`` schedules a
    ``cron_expression`` drives generation and ``publish_at`` represents
    the *next* calculated fire time.
    """

    __tablename__ = "schedules"

    channel_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("channels.id"), index=True
    )
    video_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("videos.id"), nullable=True
    )

    schedule_type: Mapped[ScheduleType] = mapped_column(
        Enum(ScheduleType), default=ScheduleType.ONE_TIME
    )
    cron_expression: Mapped[str | None] = mapped_column(
        String(100), nullable=True, doc="Cron expr for recurring, e.g. '0 14 * * 1,3,5'"
    )
    publish_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    platforms: Mapped[list] = mapped_column(
        JSON, default=lambda: ["youtube"], doc="List of platform names to publish to"
    )

    # Topic generation config (recurring schedules)
    topic_source: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default="ai"
    )
    topic_config: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        doc="Source-specific config, e.g. RSS URL or content calendar ref",
    )

    status: Mapped[ScheduleStatus] = mapped_column(
        Enum(ScheduleStatus), default=ScheduleStatus.ACTIVE
    )
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    channel: Mapped["Channel"] = relationship()  # noqa: F821
    video: Mapped["Video | None"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<Schedule {self.schedule_type.value} "
            f"[{self.status.value}] ({self.id[:8]})>"
        )
