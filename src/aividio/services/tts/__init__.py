"""Text-to-speech service — generate voice-over audio from script narration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aividio.config.settings import get_settings
from aividio.services.tts.base import TTSProvider

if TYPE_CHECKING:
    from aividio.config.settings import Settings

__all__ = ["TTSProvider", "create_tts_provider"]


def create_tts_provider(
    provider: str | None = None,
    settings: Settings | None = None,
) -> TTSProvider:
    """Factory: return a TTSProvider for the requested backend.

    Args:
        provider: ``"elevenlabs"``, ``"openai"``, ``"replicate"``, or
            ``"fal"``.  Falls back to ``settings.default_tts_provider``
            when *None*.
        settings: Optional settings override.
    """
    settings = settings or get_settings()
    provider = provider or settings.default_tts_provider

    if provider == "elevenlabs":
        from aividio.services.tts.elevenlabs import ElevenLabsTTS

        return ElevenLabsTTS(settings=settings)

    if provider == "openai":
        from aividio.services.tts.openai_tts import OpenAITTS

        return OpenAITTS(settings=settings)

    if provider == "replicate":
        from aividio.services.tts.replicate_tts import ReplicateTTS

        return ReplicateTTS(settings=settings)

    if provider == "fal":
        from aividio.services.tts.fal_tts import FalTTS

        return FalTTS(settings=settings)

    raise ValueError(f"Unknown TTS provider: {provider!r}")
