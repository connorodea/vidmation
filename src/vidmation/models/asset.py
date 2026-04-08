"""Asset model - tracks media files used in video production.

Supports two use-cases:
1. Pipeline-generated assets (stock footage, voiceovers, etc.) tied to a video.
2. User-uploaded custom assets (transitions, overlays, SFX, intros, outros,
   watermarks) available across videos.
"""

from __future__ import annotations

import enum

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vidmation.models.base import Base, TimestampMixin, UUIDMixin


class AssetType(str, enum.Enum):
    """All recognised asset categories."""

    # Pipeline-generated types (original)
    STOCK_VIDEO = "stock_video"
    STOCK_IMAGE = "stock_image"
    VOICEOVER = "voiceover"
    MUSIC = "music"
    THUMBNAIL = "thumbnail"
    CAPTION_FILE = "caption_file"
    AI_IMAGE = "ai_image"

    # User-uploadable types (custom assets system)
    TRANSITION = "transition"
    OVERLAY = "overlay"
    SOUND_EFFECT = "sound_effect"
    INTRO = "intro"
    OUTRO = "outro"
    WATERMARK = "watermark"


class AssetSource(str, enum.Enum):
    PEXELS = "pexels"
    PIXABAY = "pixabay"
    ELEVENLABS = "elevenlabs"
    OPENAI = "openai"
    DALLE = "dalle"
    REPLICATE = "replicate"
    FAL = "fal"
    WHISPER = "whisper"
    LOCAL = "local"
    UPLOAD = "upload"


class Asset(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "assets"

    # Ownership — video_id for pipeline assets, user_id for uploaded assets.
    # Both are nullable so that built-in/public assets belong to neither.
    video_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("videos.id"), nullable=True
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )

    # Descriptive
    name: Mapped[str] = mapped_column(String(255), default="")
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType))
    source: Mapped[AssetSource] = mapped_column(
        Enum(AssetSource), default=AssetSource.LOCAL
    )
    source_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # File info
    file_path: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(127), nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Visibility
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Categorisation
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    attribution: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    video: Mapped["Video"] = relationship(back_populates="assets")  # noqa: F821
    owner: Mapped["User"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        owner = f"user={self.user_id[:8]}" if self.user_id else "public"
        return f"<Asset {self.asset_type.value} '{self.name}' ({owner}, {self.id[:8]})>"
