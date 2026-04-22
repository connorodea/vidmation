"""FFmpeg utility helpers for probing and validating media files."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

import ffmpeg

logger = logging.getLogger(__name__)


class FFmpegError(Exception):
    """Raised when an FFmpeg operation fails."""


def check_ffmpeg_installed() -> bool:
    """Check whether ffmpeg and ffprobe are available on PATH."""
    ffmpeg_ok = shutil.which("ffmpeg") is not None
    ffprobe_ok = shutil.which("ffprobe") is not None
    if not ffmpeg_ok:
        logger.error("ffmpeg binary not found on PATH")
    if not ffprobe_ok:
        logger.error("ffprobe binary not found on PATH")
    return ffmpeg_ok and ffprobe_ok


def probe(path: Path) -> dict:
    """Run ffprobe on a file and return the full metadata dict.

    Raises:
        FileNotFoundError: If *path* does not exist.
        FFmpegError: If ffprobe fails.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Media file not found: {path}")

    try:
        return ffmpeg.probe(str(path))
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode() if exc.stderr else "unknown error"
        raise FFmpegError(f"ffprobe failed for {path}: {stderr}") from exc


def get_duration(path: Path) -> float:
    """Return the duration of a media file in seconds.

    Raises:
        FFmpegError: If the duration cannot be determined.
    """
    info = probe(path)

    # Prefer the format-level duration (works for both audio and video)
    fmt_duration = info.get("format", {}).get("duration")
    if fmt_duration is not None:
        return float(fmt_duration)

    # Fall back to the first stream that has a duration
    for stream in info.get("streams", []):
        if "duration" in stream:
            return float(stream["duration"])

    raise FFmpegError(f"Could not determine duration for {path}")


def get_resolution(path: Path) -> tuple[int, int]:
    """Return (width, height) of the first video stream.

    Raises:
        FFmpegError: If no video stream is found.
    """
    info = probe(path)
    for stream in info.get("streams", []):
        if stream.get("codec_type") == "video":
            width = int(stream["width"])
            height = int(stream["height"])
            return width, height

    raise FFmpegError(f"No video stream found in {path}")


def get_frame_rate(path: Path) -> float:
    """Return the frame rate (fps) of the first video stream.

    Handles both integer and fractional frame-rate strings (e.g. ``"30/1"``).

    Raises:
        FFmpegError: If no video stream is found.
    """
    info = probe(path)
    for stream in info.get("streams", []):
        if stream.get("codec_type") == "video":
            r_frame_rate = stream.get("r_frame_rate", "")
            if "/" in r_frame_rate:
                num, den = r_frame_rate.split("/")
                if int(den) == 0:
                    raise FFmpegError(f"Invalid frame rate {r_frame_rate} in {path}")
                return int(num) / int(den)
            return float(r_frame_rate)

    raise FFmpegError(f"No video stream found in {path}")


def run_ffmpeg(
    args: list[str],
    *,
    desc: str = "ffmpeg",
    timeout: int = 600,
) -> subprocess.CompletedProcess[bytes]:
    """Run an ffmpeg command with unified error handling.

    Parameters:
        args: Full argument list starting with ``"ffmpeg"``.
        desc: Human-readable description for log messages.
        timeout: Maximum seconds to allow the process to run.

    Raises:
        FFmpegError: If the command exits with a non-zero code or times out.
    """
    logger.debug("%s: running %s", desc, " ".join(args))
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise FFmpegError(f"{desc}: timed out after {timeout}s") from exc

    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace")
        raise FFmpegError(f"{desc}: ffmpeg exited {result.returncode}\n{stderr}")

    return result
