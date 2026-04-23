"""Video model - the central entity in the pipeline."""

from __future__ import annotations

import enum

from sqlalchemy import Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aividio.models.base import Base, TimestampMixin, UUIDMixin


class VideoFormat(str, enum.Enum):
    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"
    SHORT = "short"


class VideoStatus(str, enum.Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    READY = "ready"
    UPLOADED = "uploaded"
    FAILED = "failed"


class Video(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "videos"

    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    channel_id: Mapped[str] = mapped_column(String(36), ForeignKey("channels.id"))
    title: Mapped[str] = mapped_column(String(500), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[dict | list] = mapped_column(JSON, default=list)
    topic_prompt: Mapped[str] = mapped_column(Text)
    script_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    format: Mapped[VideoFormat] = mapped_column(
        Enum(VideoFormat), default=VideoFormat.LANDSCAPE
    )
    status: Mapped[VideoStatus] = mapped_column(
        Enum(VideoStatus), default=VideoStatus.DRAFT
    )
    youtube_video_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    youtube_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    channel: Mapped["Channel"] = relationship(back_populates="videos")  # noqa: F821
    jobs: Mapped[list["Job"]] = relationship(back_populates="video")  # noqa: F821
    assets: Mapped[list["Asset"]] = relationship(back_populates="video")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Video '{self.title}' [{self.status.value}] ({self.id[:8]})>"
