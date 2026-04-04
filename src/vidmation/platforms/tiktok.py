"""TikTok platform -- vertical 1080x1920, 15s-10min, no end screens.

Handles:
- Resolution reformatting to 1080x1920 (9:16 portrait).
- Smart center-crop for landscape sources, or pillarbox as fallback.
- Duration enforcement (15 seconds minimum, 10 minutes maximum).
- Metadata spec: description (2200 chars), hashtags, sounds.
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

_WIDTH = 1080
_HEIGHT = 1920
_MIN_DURATION = 15.0
_MAX_DURATION = 600.0  # 10 minutes
_MAX_FILE_SIZE_MB = 287  # TikTok upload limit (287 MB for most accounts)

_MAX_DESCRIPTION_LENGTH = 2200
_MAX_HASHTAGS = 100  # practical limit per post
_MAX_HASHTAG_LENGTH = 100


class TikTokPlatform(Platform):
    """TikTok video formatting and validation.

    Converts any source video to 1080x1920 portrait format optimised for the
    TikTok feed.  Landscape sources are center-cropped by default, preserving
    the most visually important area (centre of frame).  A pillarbox fallback
    is available for content where cropping would lose critical information.
    """

    platform_type = PlatformType.TIKTOK

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
        """Reformat a master video for TikTok upload.

        Parameters:
            video_path: Path to the source video.
            output_path: Explicit output path; derived automatically if None.
            options: Optional dict.  Recognised keys:
                - ``crop_mode``: ``"center"`` (default) -- smart center-crop
                  from landscape to portrait.  ``"pillarbox"`` -- scale with
                  black bars on top/bottom.
                - ``trim_to_max``: bool (default True) -- trim videos longer
                  than 10 minutes.

        Returns:
            Path to the TikTok-ready file.
        """
        video_path = Path(video_path)
        self._ensure_file_exists(video_path)
        options = options or {}

        if output_path is None:
            output_path = self._derive_output_path(video_path, "_tiktok")
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        src_w, src_h = get_resolution(video_path)
        src_duration = get_duration(video_path)
        crop_mode = options.get("crop_mode", "center")
        trim_to_max = options.get("trim_to_max", True)

        self.logger.info(
            "Formatting for TikTok: %dx%d (%.1fs) -> %dx%d, crop_mode=%s",
            src_w, src_h, src_duration, _WIDTH, _HEIGHT, crop_mode,
        )

        # Duration enforcement
        input_kwargs: dict[str, Any] = {}
        if trim_to_max and src_duration > _MAX_DURATION:
            self.logger.info(
                "Trimming to %.0fs for TikTok (was %.1fs)",
                _MAX_DURATION, src_duration,
            )
            input_kwargs["t"] = _MAX_DURATION

        stream = ffmpeg.input(str(video_path), **input_kwargs)
        audio = stream.audio
        video_stream = stream.video

        src_is_landscape = src_w > src_h

        if src_is_landscape and crop_mode == "center":
            video_stream = self._smart_center_crop(video_stream, src_w, src_h)
        elif src_is_landscape and crop_mode == "pillarbox":
            video_stream = self._pillarbox(video_stream)
        else:
            # Already portrait or square -- scale + pad
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
                    audio_bitrate="128k",
                    crf="20",
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
                f"TikTok formatting failed: {stderr}"
            ) from exc

        self.logger.info("TikTok-formatted video written: %s", output_path)
        return output_path

    def get_metadata_spec(self) -> dict[str, Any]:
        """Return TikTok metadata constraints.

        Returns:
            Dict describing maximum lengths and allowed fields.
        """
        return {
            "max_description_length": _MAX_DESCRIPTION_LENGTH,
            "max_hashtags": _MAX_HASHTAGS,
            "max_hashtag_length": _MAX_HASHTAG_LENGTH,
            "resolution": f"{_WIDTH}x{_HEIGHT}",
            "aspect_ratio": "9:16",
            "min_duration_seconds": _MIN_DURATION,
            "max_duration_seconds": _MAX_DURATION,
            "max_file_size_mb": _MAX_FILE_SIZE_MB,
            "supports_sounds": True,
            "supports_end_screens": False,
            "supports_tags": False,
            "supports_hashtags": True,
        }

    def validate_for_platform(self, video_path: Path) -> list[str]:
        """Check that *video_path* meets TikTok requirements.

        Returns:
            List of issue descriptions; empty if the file is compliant.
        """
        video_path = Path(video_path)
        self._ensure_file_exists(video_path)

        issues: list[str] = []

        # Resolution
        try:
            w, h = get_resolution(video_path)
            if w != _WIDTH or h != _HEIGHT:
                issues.append(
                    f"Resolution is {w}x{h}, expected {_WIDTH}x{_HEIGHT}"
                )
        except Exception as exc:
            issues.append(f"Could not read resolution: {exc}")

        # Duration
        try:
            dur = get_duration(video_path)
            if dur < _MIN_DURATION:
                issues.append(
                    f"Duration is {dur:.1f}s, TikTok minimum is {_MIN_DURATION:.0f}s"
                )
            if dur > _MAX_DURATION:
                issues.append(
                    f"Duration is {dur:.1f}s, TikTok maximum is {_MAX_DURATION:.0f}s"
                )
        except Exception as exc:
            issues.append(f"Could not read duration: {exc}")

        # File size
        file_size_mb = video_path.stat().st_size / (1024 ** 2)
        if file_size_mb > _MAX_FILE_SIZE_MB:
            issues.append(
                f"File size is {file_size_mb:.1f} MB, TikTok limit is {_MAX_FILE_SIZE_MB} MB"
            )

        return issues

    # ------------------------------------------------------------------
    # Internal ffmpeg helpers
    # ------------------------------------------------------------------

    def _smart_center_crop(
        self,
        stream: Any,
        src_w: int,
        src_h: int,
    ) -> Any:
        """Center-crop a landscape stream to 9:16 portrait, then scale.

        Computes the largest 9:16 rectangle centred within the source frame,
        crops to that region, then scales to the exact target resolution.
        """
        target_ratio = _WIDTH / _HEIGHT  # 0.5625
        crop_w = int(src_h * target_ratio)
        crop_h = src_h

        if crop_w > src_w:
            crop_w = src_w
            crop_h = int(src_w / target_ratio)

        x_offset = max(0, (src_w - crop_w) // 2)
        y_offset = max(0, (src_h - crop_h) // 2)

        self.logger.debug(
            "Smart center-crop: %dx%d -> crop %dx%d at (%d,%d) -> scale %dx%d",
            src_w, src_h, crop_w, crop_h, x_offset, y_offset, _WIDTH, _HEIGHT,
        )

        stream = stream.filter("crop", crop_w, crop_h, x_offset, y_offset)
        stream = stream.filter("scale", _WIDTH, _HEIGHT)
        stream = stream.filter("setsar", "1")
        return stream

    def _pillarbox(self, stream: Any) -> Any:
        """Scale landscape video to fit width, pad top/bottom with black bars."""
        stream = stream.filter(
            "scale",
            _WIDTH,
            _HEIGHT,
            force_original_aspect_ratio="decrease",
        )
        stream = stream.filter(
            "pad",
            _WIDTH,
            _HEIGHT,
            "(ow-iw)/2",
            "(oh-ih)/2",
            color="black",
        )
        stream = stream.filter("setsar", "1")
        return stream

    def _scale_and_pad(self, stream: Any) -> Any:
        """Scale + pad any aspect ratio to target resolution."""
        stream = stream.filter(
            "scale",
            _WIDTH,
            _HEIGHT,
            force_original_aspect_ratio="decrease",
        )
        stream = stream.filter(
            "pad",
            _WIDTH,
            _HEIGHT,
            "(ow-iw)/2",
            "(oh-ih)/2",
            color="black",
        )
        stream = stream.filter("setsar", "1")
        return stream
