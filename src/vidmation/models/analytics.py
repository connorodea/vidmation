"""Analytics models - usage tracking, cost monitoring, and video performance."""

from __future__ import annotations

import enum

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vidmation.models.base import Base, TimestampMixin, UUIDMixin


class ServiceType(str, enum.Enum):
    CLAUDE = "claude"
    OPENAI_GPT4O = "openai_gpt4o"
    ELEVENLABS = "elevenlabs"
    OPENAI_TTS = "openai_tts"
    DALLE3 = "dalle3"
    REPLICATE_FLUX = "replicate_flux"
    REPLICATE_KLING = "replicate_kling"
    FAL_FLUX = "fal_flux"
    FAL_KLING = "fal_kling"
    WHISPER_LOCAL = "whisper_local"
    WHISPER_REPLICATE = "whisper_replicate"
    PEXELS = "pexels"
    PIXABAY = "pixabay"
    YOUTUBE_UPLOAD = "youtube_upload"


class OperationType(str, enum.Enum):
    SCRIPT_GEN = "script_gen"
    TTS = "tts"
    TRANSCRIBE = "transcribe"
    SEARCH = "search"
    DOWNLOAD = "download"
    IMAGE_GEN = "image_gen"
    VIDEO_GEN = "video_gen"
    UPLOAD = "upload"
    THUMBNAIL_GEN = "thumbnail_gen"


class PeriodType(str, enum.Enum):
    DAILY = "daily"
    MONTHLY = "monthly"


class UsageEvent(Base, UUIDMixin, TimestampMixin):
    """Tracks every API call made during video generation."""

    __tablename__ = "usage_events"

    timestamp: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
    service: Mapped[str] = mapped_column(String(50), index=True)
    operation: Mapped[str] = mapped_column(String(50), index=True)
    video_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("videos.id"), nullable=True, index=True
    )
    job_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("jobs.id"), nullable=True, index=True
    )
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    video: Mapped["Video | None"] = relationship(  # noqa: F821
        "Video", foreign_keys=[video_id], lazy="joined"
    )
    job: Mapped["Job | None"] = relationship(  # noqa: F821
        "Job", foreign_keys=[job_id], lazy="joined"
    )

    def __repr__(self) -> str:
        return (
            f"<UsageEvent {self.service}/{self.operation} "
            f"${self.cost_usd:.4f} ({self.id[:8]})>"
        )


class CostSummary(Base, UUIDMixin):
    """Aggregated cost summaries by period (daily/monthly)."""

    __tablename__ = "cost_summaries"

    period_type: Mapped[str] = mapped_column(
        String(20), index=True
    )
    period_start: Mapped[str] = mapped_column(
        DateTime(timezone=True), index=True
    )
    period_end: Mapped[str] = mapped_column(DateTime(timezone=True))
    service: Mapped[str] = mapped_column(String(50), index=True)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    total_calls: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)

    def __repr__(self) -> str:
        return (
            f"<CostSummary {self.period_type} {self.service} "
            f"${self.total_cost_usd:.2f}>"
        )


class VideoAnalytics(Base, UUIDMixin):
    """Per-video YouTube performance metrics."""

    __tablename__ = "video_analytics"

    video_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("videos.id"), index=True
    )
    fetched_at: Mapped[str] = mapped_column(DateTime(timezone=True))

    # Core engagement metrics
    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    watch_time_hours: Mapped[float] = mapped_column(Float, default=0.0)

    # Viewer behavior
    avg_view_duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    avg_view_percentage: Mapped[float] = mapped_column(Float, default=0.0)

    # Discovery metrics
    click_through_rate: Mapped[float] = mapped_column(Float, default=0.0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)

    # Growth metrics
    subscriber_gain: Mapped[int] = mapped_column(Integer, default=0)

    # Detailed breakdowns stored as JSON
    traffic_sources_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    demographics_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    video: Mapped["Video"] = relationship(  # noqa: F821
        "Video", foreign_keys=[video_id], lazy="joined"
    )

    def __repr__(self) -> str:
        return (
            f"<VideoAnalytics video={self.video_id[:8]} "
            f"views={self.views} likes={self.likes}>"
        )
