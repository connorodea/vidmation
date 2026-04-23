"""Job model - tracks pipeline execution tasks."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aividio.models.base import Base, TimestampMixin, UUIDMixin


class JobType(str, enum.Enum):
    FULL_PIPELINE = "full_pipeline"
    SCRIPT_ONLY = "script_only"
    TTS_ONLY = "tts_only"
    VIDEO_ONLY = "video_only"
    UPLOAD_ONLY = "upload_only"
    THUMBNAIL_ONLY = "thumbnail_only"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "jobs"

    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id"))
    job_type: Mapped[JobType] = mapped_column(Enum(JobType), default=JobType.FULL_PIPELINE)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.QUEUED)
    current_stage: Mapped[str] = mapped_column(String(100), default="")
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)
    resume_from_stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    video: Mapped["Video"] = relationship(back_populates="jobs")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Job {self.job_type.value} [{self.status.value}] ({self.id[:8]})>"
