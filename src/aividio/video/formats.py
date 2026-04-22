"""Video format specifications for VIDMATION output targets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FormatSpec:
    """Immutable specification for a video output format."""

    name: str
    width: int
    height: int
    fps: int
    max_duration: float | None  # seconds; None = unlimited
    # FFmpeg encoding presets
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    video_bitrate: str = "8M"
    audio_bitrate: str = "192k"
    preset: str = "medium"
    crf: int = 18
    pixel_format: str = "yuv420p"
    profile: str = "high"
    level: str = "4.1"
    movflags: str = "+faststart"

    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height}"

    def ffmpeg_output_kwargs(self) -> dict[str, str]:
        """Return a dict of keyword arguments suitable for ffmpeg.output()."""
        return {
            "vcodec": self.video_codec,
            "acodec": self.audio_codec,
            "video_bitrate": self.video_bitrate,
            "audio_bitrate": self.audio_bitrate,
            "preset": self.preset,
            "crf": str(self.crf),
            "pix_fmt": self.pixel_format,
            "profile:v": self.profile,
            "level": self.level,
            "movflags": self.movflags,
        }


# ── Pre-defined formats ───────────────────────────────────────────────

LANDSCAPE = FormatSpec(
    name="landscape",
    width=1920,
    height=1080,
    fps=30,
    max_duration=None,
)

PORTRAIT = FormatSpec(
    name="portrait",
    width=1080,
    height=1920,
    fps=30,
    max_duration=None,
)

SHORT = FormatSpec(
    name="short",
    width=1080,
    height=1920,
    fps=30,
    max_duration=60.0,
    video_bitrate="6M",
    crf=20,
)

# Lookup by name
FORMAT_REGISTRY: dict[str, FormatSpec] = {
    "landscape": LANDSCAPE,
    "portrait": PORTRAIT,
    "short": SHORT,
}


def get_format(name: str) -> FormatSpec:
    """Retrieve a format spec by name.

    Raises:
        ValueError: If *name* is not a recognised format.
    """
    key = name.lower().strip()
    if key not in FORMAT_REGISTRY:
        valid = ", ".join(sorted(FORMAT_REGISTRY))
        raise ValueError(f"Unknown video format '{name}'. Valid formats: {valid}")
    return FORMAT_REGISTRY[key]
