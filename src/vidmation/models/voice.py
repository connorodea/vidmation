"""Voice model — tracks cloned and stock voices across providers."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from vidmation.models.base import Base, TimestampMixin, UUIDMixin


class Voice(Base, UUIDMixin, TimestampMixin):
    """Represents a voice available for TTS.

    Voices can be stock (pre-built by a provider) or cloned from user-supplied
    audio samples.  Each voice is tied to an external provider voice ID and
    can optionally be scoped to a specific channel.

    Attributes:
        name: Human-readable display name.
        provider: TTS provider — ``"elevenlabs"``, ``"replicate"``, or ``"fal"``.
        voice_id: External provider-specific voice identifier.
        channel_id: Optional FK to ``channels.id`` — *None* means the voice
            is globally available.
        is_cloned: Whether this voice was created via voice cloning.
        sample_path: Path to the original audio sample used for cloning.
        preview_path: Path to a generated preview audio clip.
        reference_audio_path: Path to the reference audio for inference-time
            cloning (Replicate XTTS-v2 / fal F5-TTS).
        description: Optional notes or description of the voice.
        settings_json: Provider-specific settings such as stability, speed,
            similarity_boost, etc., stored as a JSON blob.
        usage_count: Number of times this voice has been used for generation.
    """

    __tablename__ = "voices"

    name: Mapped[str] = mapped_column(String(255))
    provider: Mapped[str] = mapped_column(String(50))
    voice_id: Mapped[str] = mapped_column(String(255))

    channel_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("channels.id"),
        nullable=True,
    )

    is_cloned: Mapped[bool] = mapped_column(Boolean, default=False)

    sample_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    preview_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reference_audio_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    settings_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    usage_count: Mapped[int] = mapped_column(default=0)

    def __repr__(self) -> str:
        cloned_tag = " [cloned]" if self.is_cloned else ""
        return f"<Voice {self.name} ({self.provider}{cloned_tag})>"
