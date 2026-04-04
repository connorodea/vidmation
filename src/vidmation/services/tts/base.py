"""Abstract base class for text-to-speech providers."""

from __future__ import annotations

from abc import abstractmethod
from pathlib import Path

from vidmation.config.profiles import VoiceConfig
from vidmation.services.base import BaseService


class TTSProvider(BaseService):
    """ABC for text-to-speech services."""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice_config: VoiceConfig,
        output_path: Path,
    ) -> tuple[Path, float]:
        """Convert *text* to speech audio.

        Args:
            text: The narration text to speak.
            voice_config: Voice parameters (voice ID, stability, etc.).
            output_path: Where to write the resulting audio file.

        Returns:
            A ``(audio_path, duration_seconds)`` tuple.
        """
        ...

    @abstractmethod
    def list_voices(self) -> list[dict]:
        """Return available voices as a list of dicts.

        Each dict should contain at minimum ``{"voice_id": ..., "name": ...}``.
        """
        ...
