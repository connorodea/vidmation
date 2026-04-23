"""Abstract base class for platform-specific video formatting and validation.

Every supported target platform (YouTube, TikTok, Instagram, etc.) implements
this interface so that the :class:`MultiPlatformExporter` can treat them
uniformly.
"""

from __future__ import annotations

import enum
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PlatformType(str, enum.Enum):
    """Enumeration of supported export platforms."""

    YOUTUBE = "youtube"
    YOUTUBE_SHORTS = "youtube_shorts"
    TIKTOK = "tiktok"
    INSTAGRAM_REELS = "instagram_reels"
    INSTAGRAM_FEED = "instagram_feed"
    INSTAGRAM_STORIES = "instagram_stories"


class Platform(ABC):
    """Abstract base for a target platform.

    Subclasses must implement three methods:

    * :meth:`format_for_platform` -- re-encode / reformat a master video to
      meet the platform's resolution, duration, and codec requirements.
    * :meth:`get_metadata_spec` -- return the platform's metadata constraints
      (max title length, allowed tags, etc.).
    * :meth:`validate_for_platform` -- check an existing file against the
      platform's requirements and return a list of human-readable issues.
    """

    # Subclasses should set this to the relevant PlatformType value.
    platform_type: PlatformType

    def __init__(self) -> None:
        self.logger = logging.getLogger(
            f"aividio.platforms.{self.__class__.__name__}"
        )

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def format_for_platform(
        self,
        video_path: Path,
        output_path: Path | None = None,
        *,
        options: dict[str, Any] | None = None,
    ) -> Path:
        """Reformat *video_path* to meet this platform's requirements.

        Parameters:
            video_path: Path to the master (source) video.
            output_path: Optional explicit output path.  If ``None`` the
                implementation should derive a sensible path (e.g. alongside
                the source with a platform suffix).
            options: Platform-specific knobs (crop mode, quality, etc.).

        Returns:
            Path to the reformatted video file.

        Raises:
            FileNotFoundError: If *video_path* does not exist.
            aividio.utils.ffmpeg.FFmpegError: On encoding failure.
        """
        ...

    @abstractmethod
    def get_metadata_spec(self) -> dict[str, Any]:
        """Return metadata constraints for this platform.

        The returned dict describes maximum lengths, required fields, allowed
        values, etc.  Example keys: ``max_title_length``, ``max_description_length``,
        ``max_tags_total_chars``, ``allowed_visibilities``.

        Returns:
            A JSON-serialisable dict of constraint descriptions.
        """
        ...

    @abstractmethod
    def validate_for_platform(self, video_path: Path) -> list[str]:
        """Validate that *video_path* meets this platform's constraints.

        Checks resolution, duration, codec, file size, etc.

        Parameters:
            video_path: Path to the video file to validate.

        Returns:
            A list of human-readable issue descriptions.  An empty list means
            the file passes all checks.

        Raises:
            FileNotFoundError: If *video_path* does not exist.
        """
        ...

    # ------------------------------------------------------------------
    # Helpers available to subclasses
    # ------------------------------------------------------------------

    def _ensure_file_exists(self, path: Path) -> None:
        """Raise :class:`FileNotFoundError` if *path* does not exist."""
        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {path}")

    def _derive_output_path(self, video_path: Path, suffix: str) -> Path:
        """Derive an output path by inserting *suffix* before the extension.

        Example: ``/tmp/master.mp4`` with suffix ``"_youtube"`` becomes
        ``/tmp/master_youtube.mp4``.
        """
        stem = video_path.stem
        ext = video_path.suffix or ".mp4"
        return video_path.with_name(f"{stem}{suffix}{ext}")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} ({self.platform_type.value})>"
