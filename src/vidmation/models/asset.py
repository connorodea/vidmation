"""Asset model - tracks media files used in video production."""

from __future__ import annotations

import enum

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vidmation.models.base import Base, TimestampMixin, UUIDMixin


class AssetType(str, enum.Enum):
    STOCK_VIDEO = "stock_video"
    STOCK_IMAGE = "stock_image"
    VOICEOVER = "voiceover"
    MUSIC = "music"
    THUMBNAIL = "thumbnail"
    CAPTION_FILE = "caption_file"
    AI_IMAGE = "ai_image"


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


class Asset(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "assets"

    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id"))
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType))
    source: Mapped[AssetSource] = mapped_column(Enum(AssetSource))
    source_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str] = mapped_column(String(500))
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    attribution: Mapped[str | None] = mapped_column(Text, nullable=True)

    video: Mapped["Video"] = relationship(back_populates="assets")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Asset {self.asset_type.value} from {self.source.value} ({self.id[:8]})>"
