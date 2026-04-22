"""Abstract base class for AI avatar (talking-head) providers."""

from __future__ import annotations

from abc import abstractmethod
from pathlib import Path

from aividio.config.profiles import VoiceConfig
from aividio.services.base import BaseService


class AvatarProvider(BaseService):
    """ABC for AI talking-head avatar video generators.

    An avatar provider takes a text script (or pre-generated audio), an
    avatar reference image/video, and voice configuration, then produces
    a video of a talking head speaking the script.
    """

    @abstractmethod
    def generate(
        self,
        text: str,
        avatar_id: str,
        voice_config: VoiceConfig,
        output_path: Path,
        *,
        audio_path: Path | None = None,
    ) -> Path:
        """Generate an avatar video speaking the given text.

        Args:
            text: The narration script.
            avatar_id: Identifier for the avatar preset or reference image.
            voice_config: Voice parameters for TTS (used when *audio_path*
                is not provided).
            output_path: Where to write the resulting video file.
            audio_path: Optional pre-generated audio; if provided, TTS is
                skipped and this audio is used for lip-sync.

        Returns:
            Path to the generated avatar video file.
        """
        ...

    @abstractmethod
    def list_avatars(self) -> list[dict]:
        """Return available avatar presets.

        Each dict should contain at minimum::

            {"avatar_id": ..., "name": ..., "preview_url": ...}
        """
        ...

    @abstractmethod
    def create_avatar(
        self,
        video_sample: Path,
        name: str,
        description: str = "",
    ) -> dict:
        """Create a custom avatar from a video sample.

        Args:
            video_sample: Path to a short video of the person (ideally
                5--30 seconds, front-facing, good lighting).
            name: Human-readable name for the avatar.
            description: Optional description.

        Returns:
            A dict with ``avatar_id``, ``name``, ``provider``, and
            ``preview_url`` (if available).
        """
        ...
