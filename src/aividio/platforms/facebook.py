"""Facebook platform -- landscape 1920x1080 or square 1080x1080 video.

Handles:
- Resolution reformatting to 1920x1080 (landscape) or 1080x1080 (square).
- Duration enforcement (1 second minimum, 240 minutes maximum).
- File size limit of 10 GB.
- Metadata spec: title (100 chars), description (no hard limit, 500 recommended).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import ffmpeg

from aividio.platforms.base import Platform, PlatformType
from aividio.utils.ffmpeg import FFmpegError, get_duration, get_resolution

logger = logging.getLogger(__name__)

_LANDSCAPE_WIDTH = 1920
_LANDSCAPE_HEIGHT = 1080
_SQUARE_WIDTH = 1080
_SQUARE_HEIGHT = 1080
_MIN_DURATION = 1.0
_MAX_DURATION = 14400.0  # 240 minutes
_MAX_FILE_SIZE_MB = 10240  # 10 GB


class FacebookPlatform(Platform):
    """Facebook video formatting and validation."""

    platform_type = PlatformType.YOUTUBE  # Re-use; no FB enum yet

    def __init__(self, sub_format: str = "landscape") -> None:
        super().__init__()
        self._sub_format = sub_format

    def format_for_platform(
        self,
        video_path: Path,
        output_path: Path | None = None,
        *,
        options: dict[str, Any] | None = None,
    ) -> Path:
        """Reformat a master video for Facebook."""
        self._ensure_file_exists(video_path)
        options = options or {}

        sub_format = options.get("sub_format", self._sub_format)
        if sub_format == "square":
            target_w, target_h = _SQUARE_WIDTH, _SQUARE_HEIGHT
        else:
            target_w, target_h = _LANDSCAPE_WIDTH, _LANDSCAPE_HEIGHT

        if output_path is None:
            output_path = self._derive_output_path(video_path, f"_facebook_{sub_format}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        src_w, src_h = get_resolution(video_path)

        self.logger.info(
            "Facebook export: %dx%d -> %dx%d (%s)",
            src_w, src_h, target_w, target_h, sub_format,
        )

        try:
            stream = ffmpeg.input(str(video_path))

            if sub_format == "square" and src_w != src_h:
                # Center-crop to square
                crop_size = min(src_w, src_h)
                stream = stream.filter(
                    "crop", crop_size, crop_size,
                    f"(iw-{crop_size})/2", f"(ih-{crop_size})/2",
                )

            stream = stream.filter("scale", target_w, target_h,
                                   force_original_aspect_ratio="decrease")
            stream = stream.filter("pad", target_w, target_h,
                                   "(ow-iw)/2", "(oh-ih)/2", color="black")
            stream = stream.filter("setsar", "1")

            (
                stream
                .output(
                    str(output_path),
                    vcodec="libx264", acodec="aac",
                    crf="20", preset="fast",
                    pix_fmt="yuv420p",
                    audio_bitrate="192k",
                    movflags="+faststart",
                )
                .overwrite_output()
                .run(quiet=True)
            )
        except ffmpeg.Error as exc:
            stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
            raise FFmpegError(f"Facebook export failed: {stderr}") from exc

        self.logger.info("Facebook export complete: %s", output_path)
        return output_path

    def get_metadata_spec(self) -> dict[str, Any]:
        return {
            "platform": "facebook",
            "max_title_length": 100,
            "max_description_length": 5000,
            "max_duration_seconds": _MAX_DURATION,
            "min_duration_seconds": _MIN_DURATION,
            "max_file_size_mb": _MAX_FILE_SIZE_MB,
            "supported_formats": ["landscape", "square"],
            "recommended_resolution": "1920x1080",
        }

    def validate_for_platform(self, video_path: Path) -> list[str]:
        self._ensure_file_exists(video_path)
        issues: list[str] = []

        duration = get_duration(video_path)
        if duration < _MIN_DURATION:
            issues.append(f"Duration {duration:.1f}s is below minimum {_MIN_DURATION}s")
        if duration > _MAX_DURATION:
            issues.append(f"Duration {duration:.1f}s exceeds maximum {_MAX_DURATION}s")

        file_size_mb = video_path.stat().st_size / (1024 * 1024)
        if file_size_mb > _MAX_FILE_SIZE_MB:
            issues.append(f"File size {file_size_mb:.0f}MB exceeds {_MAX_FILE_SIZE_MB}MB limit")

        return issues
