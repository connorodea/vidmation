"""Instagram platform -- Reels (1080x1920), Feed (1080x1080), Stories (1080x1920).

Handles:
- Reels: 1080x1920 portrait, 15-90 seconds.
- Feed: 1080x1080 square, up to 60 seconds.
- Stories: 1080x1920 portrait, auto-split into 15-second segments.
- Auto-reformatting with platform-specific caption styles.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any

import ffmpeg

from vidmation.platforms.base import Platform, PlatformType
from vidmation.utils.ffmpeg import FFmpegError, get_duration, get_resolution

logger = logging.getLogger(__name__)

# ── Reels constants ──────────────────────────────────────────────────────────

_REELS_WIDTH = 1080
_REELS_HEIGHT = 1920
_REELS_MIN_DURATION = 15.0
_REELS_MAX_DURATION = 90.0

# ── Feed constants ───────────────────────────────────────────────────────────

_FEED_WIDTH = 1080
_FEED_HEIGHT = 1080
_FEED_MAX_DURATION = 60.0

# ── Stories constants ────────────────────────────────────────────────────────

_STORIES_WIDTH = 1080
_STORIES_HEIGHT = 1920
_STORIES_SEGMENT_DURATION = 15.0

# ── Shared constants ─────────────────────────────────────────────────────────

_MAX_CAPTION_LENGTH = 2200
_MAX_HASHTAGS = 30
_MAX_FILE_SIZE_MB = 250


# ── Sub-format configs ───────────────────────────────────────────────────────

_FORMAT_CONFIGS: dict[PlatformType, dict[str, Any]] = {
    PlatformType.INSTAGRAM_REELS: {
        "width": _REELS_WIDTH,
        "height": _REELS_HEIGHT,
        "min_duration": _REELS_MIN_DURATION,
        "max_duration": _REELS_MAX_DURATION,
        "aspect_ratio": "9:16",
        "suffix": "_ig_reels",
    },
    PlatformType.INSTAGRAM_FEED: {
        "width": _FEED_WIDTH,
        "height": _FEED_HEIGHT,
        "min_duration": None,
        "max_duration": _FEED_MAX_DURATION,
        "aspect_ratio": "1:1",
        "suffix": "_ig_feed",
    },
    PlatformType.INSTAGRAM_STORIES: {
        "width": _STORIES_WIDTH,
        "height": _STORIES_HEIGHT,
        "min_duration": None,
        "max_duration": None,  # unlimited -- auto-segmented
        "aspect_ratio": "9:16",
        "suffix": "_ig_story",
    },
}


class InstagramPlatform(Platform):
    """Instagram video formatting and validation.

    Supports three sub-formats selectable via the *sub_format* constructor
    argument:

    * **reels** (default) -- 1080x1920, 15-90 s.
    * **feed** -- 1080x1080 square, up to 60 s.
    * **stories** -- 1080x1920, automatically split into 15 s segments.
    """

    platform_type = PlatformType.INSTAGRAM_REELS

    def __init__(self, sub_format: str = "reels") -> None:
        super().__init__()
        sub_format = sub_format.lower().strip()
        mapping = {
            "reels": PlatformType.INSTAGRAM_REELS,
            "feed": PlatformType.INSTAGRAM_FEED,
            "stories": PlatformType.INSTAGRAM_STORIES,
        }
        if sub_format not in mapping:
            raise ValueError(
                f"Unknown Instagram sub-format '{sub_format}'. "
                f"Valid: {', '.join(sorted(mapping))}"
            )
        self.platform_type = mapping[sub_format]
        self.sub_format = sub_format
        self._config = _FORMAT_CONFIGS[self.platform_type]

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
        """Reformat a master video for Instagram upload.

        For **stories** this returns the path to the *first* segment;
        additional segments are written as ``*_ig_story_001.mp4``,
        ``*_ig_story_002.mp4``, etc.  Use :meth:`format_stories` directly
        to get the full list of segment paths.

        Parameters:
            video_path: Path to the source video.
            output_path: Explicit output path (or directory for stories).
            options: Optional dict.  Recognised keys:
                - ``crop_mode``: ``"center"`` (default) or ``"pillarbox"``.

        Returns:
            Path to the reformatted video (or first story segment).
        """
        video_path = Path(video_path)
        self._ensure_file_exists(video_path)
        options = options or {}

        if self.sub_format == "stories":
            segments = self.format_stories(video_path, output_dir=output_path, options=options)
            return segments[0] if segments else video_path

        suffix: str = self._config["suffix"]
        if output_path is None:
            output_path = self._derive_output_path(video_path, suffix)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        target_w: int = self._config["width"]
        target_h: int = self._config["height"]

        src_w, src_h = get_resolution(video_path)
        src_duration = get_duration(video_path)
        crop_mode = options.get("crop_mode", "center")

        self.logger.info(
            "Formatting for Instagram %s: %dx%d (%.1fs) -> %dx%d",
            self.sub_format, src_w, src_h, src_duration, target_w, target_h,
        )

        # Duration trimming
        max_dur: float | None = self._config["max_duration"]
        input_kwargs: dict[str, Any] = {}
        if max_dur and src_duration > max_dur:
            self.logger.info(
                "Trimming to %.0fs for Instagram %s (was %.1fs)",
                max_dur, self.sub_format, src_duration,
            )
            input_kwargs["t"] = max_dur

        stream = ffmpeg.input(str(video_path), **input_kwargs)
        audio = stream.audio
        video_stream = stream.video

        src_is_landscape = src_w > src_h
        target_is_portrait = target_h > target_w
        target_is_square = target_w == target_h

        if target_is_square:
            video_stream = self._crop_to_square(video_stream, src_w, src_h, crop_mode)
        elif src_is_landscape and target_is_portrait and crop_mode == "center":
            video_stream = self._center_crop_to_portrait(
                video_stream, src_w, src_h, target_w, target_h,
            )
        else:
            video_stream = self._scale_and_pad(video_stream, target_w, target_h)

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
                f"Instagram {self.sub_format} formatting failed: {stderr}"
            ) from exc

        self.logger.info(
            "Instagram %s video written: %s", self.sub_format, output_path,
        )
        return output_path

    def format_stories(
        self,
        video_path: Path,
        output_dir: Path | None = None,
        *,
        options: dict[str, Any] | None = None,
    ) -> list[Path]:
        """Split a video into 15-second Instagram Story segments.

        Parameters:
            video_path: Path to the source video.
            output_dir: Directory for segment files.  If None, segments are
                placed alongside the source file.
            options: Optional dict.  Recognised keys:
                - ``crop_mode``: ``"center"`` (default) or ``"pillarbox"``.

        Returns:
            Ordered list of segment file paths.
        """
        video_path = Path(video_path)
        self._ensure_file_exists(video_path)
        options = options or {}

        if output_dir is None:
            output_dir = video_path.parent
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        src_duration = get_duration(video_path)
        src_w, src_h = get_resolution(video_path)
        crop_mode = options.get("crop_mode", "center")
        num_segments = max(1, math.ceil(src_duration / _STORIES_SEGMENT_DURATION))

        self.logger.info(
            "Splitting %.1fs video into %d story segments (15s each)",
            src_duration, num_segments,
        )

        segment_paths: list[Path] = []

        for i in range(num_segments):
            start_time = i * _STORIES_SEGMENT_DURATION
            segment_dur = min(_STORIES_SEGMENT_DURATION, src_duration - start_time)
            if segment_dur <= 0:
                break

            seg_name = f"{video_path.stem}_ig_story_{i + 1:03d}.mp4"
            seg_path = output_dir / seg_name

            stream = ffmpeg.input(str(video_path), ss=start_time, t=segment_dur)
            audio = stream.audio
            video_stream = stream.video

            src_is_landscape = src_w > src_h
            if src_is_landscape and crop_mode == "center":
                video_stream = self._center_crop_to_portrait(
                    video_stream, src_w, src_h, _STORIES_WIDTH, _STORIES_HEIGHT,
                )
            else:
                video_stream = self._scale_and_pad(
                    video_stream, _STORIES_WIDTH, _STORIES_HEIGHT,
                )

            try:
                (
                    ffmpeg
                    .output(
                        video_stream,
                        audio,
                        str(seg_path),
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
                    f"Instagram story segment {i + 1} failed: {stderr}"
                ) from exc

            self.logger.info("Story segment %d/%d: %s", i + 1, num_segments, seg_path)
            segment_paths.append(seg_path)

        return segment_paths

    def get_metadata_spec(self) -> dict[str, Any]:
        """Return Instagram metadata constraints for the configured sub-format.

        Returns:
            Dict with keys describing maximum lengths and allowed values.
        """
        spec: dict[str, Any] = {
            "max_caption_length": _MAX_CAPTION_LENGTH,
            "max_hashtags": _MAX_HASHTAGS,
            "max_file_size_mb": _MAX_FILE_SIZE_MB,
            "resolution": f"{self._config['width']}x{self._config['height']}",
            "aspect_ratio": self._config["aspect_ratio"],
            "supports_end_screens": False,
            "supports_sounds": True,
            "sub_format": self.sub_format,
        }
        if self._config["min_duration"] is not None:
            spec["min_duration_seconds"] = self._config["min_duration"]
        if self._config["max_duration"] is not None:
            spec["max_duration_seconds"] = self._config["max_duration"]
        if self.sub_format == "stories":
            spec["segment_duration_seconds"] = _STORIES_SEGMENT_DURATION
        return spec

    def validate_for_platform(self, video_path: Path) -> list[str]:
        """Check that *video_path* meets Instagram requirements for the
        configured sub-format.

        Returns:
            List of issue descriptions; empty if the file is compliant.
        """
        video_path = Path(video_path)
        self._ensure_file_exists(video_path)

        issues: list[str] = []
        target_w: int = self._config["width"]
        target_h: int = self._config["height"]

        # Resolution
        try:
            w, h = get_resolution(video_path)
            if w != target_w or h != target_h:
                issues.append(
                    f"Resolution is {w}x{h}, expected {target_w}x{target_h} "
                    f"for Instagram {self.sub_format}"
                )
        except Exception as exc:
            issues.append(f"Could not read resolution: {exc}")

        # Duration
        try:
            dur = get_duration(video_path)
            min_dur = self._config.get("min_duration")
            max_dur = self._config.get("max_duration")
            if min_dur and dur < min_dur:
                issues.append(
                    f"Duration is {dur:.1f}s, Instagram {self.sub_format} "
                    f"minimum is {min_dur:.0f}s"
                )
            if max_dur and dur > max_dur:
                issues.append(
                    f"Duration is {dur:.1f}s, Instagram {self.sub_format} "
                    f"maximum is {max_dur:.0f}s"
                )
        except Exception as exc:
            issues.append(f"Could not read duration: {exc}")

        # File size
        file_size_mb = video_path.stat().st_size / (1024 ** 2)
        if file_size_mb > _MAX_FILE_SIZE_MB:
            issues.append(
                f"File size is {file_size_mb:.1f} MB, Instagram limit is {_MAX_FILE_SIZE_MB} MB"
            )

        return issues

    # ------------------------------------------------------------------
    # Internal ffmpeg helpers
    # ------------------------------------------------------------------

    def _crop_to_square(
        self,
        stream: Any,
        src_w: int,
        src_h: int,
        crop_mode: str,
    ) -> Any:
        """Crop video to a square (1:1) region, then scale to target."""
        side = min(src_w, src_h)

        if crop_mode == "center":
            x_offset = max(0, (src_w - side) // 2)
            y_offset = max(0, (src_h - side) // 2)
            self.logger.debug(
                "Square crop: %dx%d -> %dx%d at (%d,%d)",
                src_w, src_h, side, side, x_offset, y_offset,
            )
            stream = stream.filter("crop", side, side, x_offset, y_offset)
        else:
            # Pillarbox/letterbox to square
            stream = stream.filter(
                "scale", _FEED_WIDTH, _FEED_HEIGHT,
                force_original_aspect_ratio="decrease",
            )
            stream = stream.filter(
                "pad", _FEED_WIDTH, _FEED_HEIGHT,
                "(ow-iw)/2", "(oh-ih)/2", color="black",
            )
            stream = stream.filter("setsar", "1")
            return stream

        stream = stream.filter("scale", _FEED_WIDTH, _FEED_HEIGHT)
        stream = stream.filter("setsar", "1")
        return stream

    def _center_crop_to_portrait(
        self,
        stream: Any,
        src_w: int,
        src_h: int,
        target_w: int,
        target_h: int,
    ) -> Any:
        """Center-crop a landscape stream to 9:16 portrait, then scale."""
        target_ratio = target_w / target_h
        crop_w = int(src_h * target_ratio)
        crop_h = src_h

        if crop_w > src_w:
            crop_w = src_w
            crop_h = int(src_w / target_ratio)

        x_offset = max(0, (src_w - crop_w) // 2)
        y_offset = max(0, (src_h - crop_h) // 2)

        self.logger.debug(
            "Center-crop to portrait: %dx%d -> %dx%d at (%d,%d) -> %dx%d",
            src_w, src_h, crop_w, crop_h, x_offset, y_offset, target_w, target_h,
        )

        stream = stream.filter("crop", crop_w, crop_h, x_offset, y_offset)
        stream = stream.filter("scale", target_w, target_h)
        stream = stream.filter("setsar", "1")
        return stream

    def _scale_and_pad(
        self,
        stream: Any,
        target_w: int,
        target_h: int,
    ) -> Any:
        """Scale maintaining aspect ratio, then pad to target resolution."""
        stream = stream.filter(
            "scale", target_w, target_h,
            force_original_aspect_ratio="decrease",
        )
        stream = stream.filter(
            "pad", target_w, target_h,
            "(ow-iw)/2", "(oh-ih)/2", color="black",
        )
        stream = stream.filter("setsar", "1")
        return stream
