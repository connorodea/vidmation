"""YouTube platform -- landscape (1920x1080) and Shorts (1080x1920, <60s).

Handles:
- Resolution scaling / padding to 1920x1080 (landscape) or 1080x1920 (Shorts).
- Duration enforcement (Shorts must be < 60 s).
- End-screen placeholder reservation (last 20 s for landscape uploads).
- Metadata spec: title (100 chars), description (5000 chars), tags (500 chars
  total), category_id, visibility.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import ffmpeg

from vidmation.platforms.base import Platform, PlatformType
from vidmation.utils.ffmpeg import FFmpegError, get_duration, get_resolution

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

_LANDSCAPE_WIDTH = 1920
_LANDSCAPE_HEIGHT = 1080
_SHORTS_WIDTH = 1080
_SHORTS_HEIGHT = 1920
_SHORTS_MAX_DURATION = 60.0
_END_SCREEN_DURATION = 20.0  # YouTube end-screen overlay zone (last 20 s)

_MAX_TITLE_LENGTH = 100
_MAX_DESCRIPTION_LENGTH = 5000
_MAX_TAGS_TOTAL_CHARS = 500
_ALLOWED_VISIBILITIES = ("public", "unlisted", "private")

_VALID_CATEGORY_IDS = {
    "1": "Film & Animation",
    "2": "Autos & Vehicles",
    "10": "Music",
    "15": "Pets & Animals",
    "17": "Sports",
    "19": "Travel & Events",
    "20": "Gaming",
    "22": "People & Blogs",
    "23": "Comedy",
    "24": "Entertainment",
    "25": "News & Politics",
    "26": "Howto & Style",
    "27": "Education",
    "28": "Science & Technology",
    "29": "Nonprofits & Activism",
}


class YouTubePlatform(Platform):
    """YouTube video formatting and validation.

    Supports two sub-formats:

    * **landscape** -- standard 16:9 (1920x1080).  Automatically reserves the
      last 20 seconds as an end-screen placeholder zone.
    * **shorts** -- vertical 9:16 (1080x1920), max 60 seconds.  No end screens.
    """

    platform_type = PlatformType.YOUTUBE

    def __init__(self, shorts: bool = False) -> None:
        super().__init__()
        self.shorts = shorts
        if shorts:
            self.platform_type = PlatformType.YOUTUBE_SHORTS
        self.target_width = _SHORTS_WIDTH if shorts else _LANDSCAPE_WIDTH
        self.target_height = _SHORTS_HEIGHT if shorts else _LANDSCAPE_HEIGHT

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def format_for_platform(
        self,
        video_path: Path,
        output_path: Path | None = None,
        *,
        options: dict[str, Any] | None = None,
    ) -> Path:
        """Reformat a master video for YouTube upload.

        For landscape videos the source is scaled/padded to 1920x1080 and the
        last 20 seconds are flagged as end-screen territory (via metadata, not
        visual alteration).

        For Shorts the source is cropped/scaled to 1080x1920 and trimmed to
        60 seconds maximum.

        Parameters:
            video_path: Path to the source video.
            output_path: Explicit output path; derived automatically if None.
            options: Optional dict.  Recognised keys:
                - ``crop_mode``: ``"center"`` (default) or ``"pillarbox"`` for
                  landscape-to-portrait conversion.
                - ``add_end_screen_placeholder``: bool (default True for landscape).

        Returns:
            Path to the YouTube-ready file.
        """
        video_path = Path(video_path)
        self._ensure_file_exists(video_path)
        options = options or {}

        suffix = "_yt_shorts" if self.shorts else "_youtube"
        if output_path is None:
            output_path = self._derive_output_path(video_path, suffix)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        src_w, src_h = get_resolution(video_path)
        src_duration = get_duration(video_path)
        crop_mode = options.get("crop_mode", "center")

        self.logger.info(
            "Formatting for YouTube%s: %dx%d (%.1fs) -> %dx%d",
            " Shorts" if self.shorts else "",
            src_w, src_h, src_duration,
            self.target_width, self.target_height,
        )

        stream = ffmpeg.input(str(video_path))
        audio = stream.audio

        # Duration enforcement for Shorts
        if self.shorts and src_duration > _SHORTS_MAX_DURATION:
            self.logger.info(
                "Trimming to %.0fs for YouTube Shorts (was %.1fs)",
                _SHORTS_MAX_DURATION, src_duration,
            )
            stream = ffmpeg.input(str(video_path), t=_SHORTS_MAX_DURATION)
            audio = stream.audio

        video_stream = stream.video

        # Determine if we need to crop (landscape->portrait) or just scale+pad
        src_is_landscape = src_w > src_h
        target_is_portrait = self.target_height > self.target_width

        if src_is_landscape and target_is_portrait and crop_mode == "center":
            # Center-crop landscape to portrait
            video_stream = self._center_crop_to_portrait(video_stream, src_w, src_h)
        else:
            # Scale maintaining aspect ratio, then pad
            video_stream = self._scale_and_pad(video_stream)

        try:
            (
                ffmpeg
                .output(
                    video_stream,
                    audio,
                    str(output_path),
                    vcodec="libx264",
                    acodec="aac",
                    audio_bitrate="192k",
                    crf="18",
                    preset="medium",
                    pix_fmt="yuv420p",
                    movflags="+faststart",
                    **{"profile:v": "high", "level": "4.1"},
                )
                .overwrite_output()
                .run(quiet=True)
            )
        except ffmpeg.Error as exc:
            stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
            raise FFmpegError(
                f"YouTube formatting failed: {stderr}"
            ) from exc

        self.logger.info("YouTube-formatted video written: %s", output_path)
        return output_path

    def get_metadata_spec(self) -> dict[str, Any]:
        """Return YouTube metadata constraints.

        Returns:
            Dict with keys describing maximum lengths and allowed values.
        """
        spec: dict[str, Any] = {
            "max_title_length": _MAX_TITLE_LENGTH,
            "max_description_length": _MAX_DESCRIPTION_LENGTH,
            "max_tags_total_chars": _MAX_TAGS_TOTAL_CHARS,
            "allowed_visibilities": list(_ALLOWED_VISIBILITIES),
            "valid_category_ids": dict(_VALID_CATEGORY_IDS),
            "resolution": f"{self.target_width}x{self.target_height}",
            "aspect_ratio": "16:9" if not self.shorts else "9:16",
            "supports_end_screens": not self.shorts,
            "end_screen_zone_seconds": _END_SCREEN_DURATION if not self.shorts else 0,
        }
        if self.shorts:
            spec["max_duration_seconds"] = _SHORTS_MAX_DURATION
        return spec

    def validate_for_platform(self, video_path: Path) -> list[str]:
        """Check that *video_path* meets YouTube requirements.

        Returns:
            List of issue descriptions; empty if the file is compliant.
        """
        video_path = Path(video_path)
        self._ensure_file_exists(video_path)

        issues: list[str] = []

        # Resolution check
        try:
            w, h = get_resolution(video_path)
            if w != self.target_width or h != self.target_height:
                issues.append(
                    f"Resolution is {w}x{h}, expected {self.target_width}x{self.target_height}"
                )
        except Exception as exc:
            issues.append(f"Could not read resolution: {exc}")

        # Duration check (Shorts only)
        if self.shorts:
            try:
                dur = get_duration(video_path)
                if dur > _SHORTS_MAX_DURATION:
                    issues.append(
                        f"Duration is {dur:.1f}s, YouTube Shorts maximum is "
                        f"{_SHORTS_MAX_DURATION:.0f}s"
                    )
            except Exception as exc:
                issues.append(f"Could not read duration: {exc}")

        # File size (YouTube limit is 256 GB, practically irrelevant but check)
        file_size_gb = video_path.stat().st_size / (1024 ** 3)
        if file_size_gb > 256:
            issues.append(f"File size is {file_size_gb:.1f} GB, YouTube limit is 256 GB")

        return issues

    # ------------------------------------------------------------------
    # End-screen helpers
    # ------------------------------------------------------------------

    def get_end_screen_timestamp(self, video_path: Path) -> float | None:
        """Return the timestamp (seconds) where the end-screen zone begins.

        Returns ``None`` if this is a Shorts upload (no end-screen support).
        """
        if self.shorts:
            return None

        try:
            duration = get_duration(video_path)
        except Exception:
            return None

        if duration <= _END_SCREEN_DURATION:
            return 0.0
        return duration - _END_SCREEN_DURATION

    # ------------------------------------------------------------------
    # Internal ffmpeg helpers
    # ------------------------------------------------------------------

    def _center_crop_to_portrait(
        self,
        stream: Any,
        src_w: int,
        src_h: int,
    ) -> Any:
        """Center-crop a landscape stream to 9:16 portrait ratio, then scale."""
        target_ratio = self.target_width / self.target_height  # 9/16
        crop_w = int(src_h * target_ratio)
        crop_h = src_h
        if crop_w > src_w:
            crop_w = src_w
            crop_h = int(src_w / target_ratio)

        x_offset = max(0, (src_w - crop_w) // 2)
        y_offset = max(0, (src_h - crop_h) // 2)

        self.logger.debug(
            "Center-crop: %dx%d -> %dx%d (offset %d,%d) then scale to %dx%d",
            src_w, src_h, crop_w, crop_h, x_offset, y_offset,
            self.target_width, self.target_height,
        )

        stream = stream.filter("crop", crop_w, crop_h, x_offset, y_offset)
        stream = stream.filter("scale", self.target_width, self.target_height)
        stream = stream.filter("setsar", "1")
        return stream

    def _scale_and_pad(self, stream: Any) -> Any:
        """Scale maintaining aspect ratio, then pad to target resolution."""
        stream = stream.filter(
            "scale",
            self.target_width,
            self.target_height,
            force_original_aspect_ratio="decrease",
        )
        stream = stream.filter(
            "pad",
            self.target_width,
            self.target_height,
            "(ow-iw)/2",
            "(oh-ih)/2",
            color="black",
        )
        stream = stream.filter("setsar", "1")
        return stream
