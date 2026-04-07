"""X/Twitter platform -- landscape 1280x720 or square 720x720, max 2:20.

Handles:
- Resolution reformatting to 1280x720 (landscape) or 720x720 (square).
- Duration enforcement (0.5 second minimum, 140 seconds maximum).
- File size limit of 512 MB.
- Metadata spec: tweet (280 chars), hashtags.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import ffmpeg

from vidmation.platforms.base import Platform, PlatformType
from vidmation.utils.ffmpeg import FFmpegError, get_duration, get_resolution

logger = logging.getLogger(__name__)

_WIDTH = 1280
_HEIGHT = 720
_MIN_DURATION = 0.5
_MAX_DURATION = 140.0  # 2 minutes 20 seconds
_MAX_FILE_SIZE_MB = 512


class TwitterPlatform(Platform):
    """X/Twitter video formatting and validation."""

    platform_type = PlatformType.YOUTUBE  # Re-use enum for now

    def format_for_platform(
        self,
        video_path: Path,
        output_path: Path | None = None,
        *,
        options: dict[str, Any] | None = None,
    ) -> Path:
        """Reformat a master video for X/Twitter."""
        self._ensure_file_exists(video_path)
        options = options or {}

        target_w = options.get("width", _WIDTH)
        target_h = options.get("height", _HEIGHT)

        if output_path is None:
            output_path = self._derive_output_path(video_path, "_twitter")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        src_w, src_h = get_resolution(video_path)
        duration = get_duration(video_path)

        self.logger.info(
            "Twitter export: %dx%d -> %dx%d (%.1fs)",
            src_w, src_h, target_w, target_h, duration,
        )

        try:
            stream = ffmpeg.input(str(video_path))

            # Trim to max duration if needed
            if duration > _MAX_DURATION:
                stream = ffmpeg.input(str(video_path), t=_MAX_DURATION)
                self.logger.info("Trimming to %.0fs for Twitter limit", _MAX_DURATION)

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
                    crf="23", preset="fast",
                    pix_fmt="yuv420p",
                    audio_bitrate="128k",
                    movflags="+faststart",
                )
                .overwrite_output()
                .run(quiet=True)
            )
        except ffmpeg.Error as exc:
            stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
            raise FFmpegError(f"Twitter export failed: {stderr}") from exc

        self.logger.info("Twitter export complete: %s", output_path)
        return output_path

    def get_metadata_spec(self) -> dict[str, Any]:
        return {
            "platform": "twitter",
            "max_tweet_length": 280,
            "max_duration_seconds": _MAX_DURATION,
            "min_duration_seconds": _MIN_DURATION,
            "max_file_size_mb": _MAX_FILE_SIZE_MB,
            "recommended_resolution": "1280x720",
            "max_hashtags": 5,
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
