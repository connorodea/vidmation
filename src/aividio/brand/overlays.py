"""Overlay engine -- ffmpeg-python filter graphs for brand elements on video.

Provides functions to burn logos, watermarks, lower thirds, and arbitrary text
overlays onto video files.  All operations are implemented as pure ffmpeg
filter graphs using the ``ffmpeg-python`` bindings, so no external libraries
beyond ffmpeg are required.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import ffmpeg

from aividio.utils.ffmpeg import FFmpegError

logger = logging.getLogger(__name__)

# ── Position mapping ─────────────────────────────────────────────────────────

# Maps human-readable position names to ffmpeg overlay x:y expressions.
# W/H = main video width/height, w/h = overlay width/height.
_POSITION_MAP: dict[str, tuple[str, str]] = {
    "top_left": ("20", "20"),
    "top_center": ("(W-w)/2", "20"),
    "top_right": ("W-w-20", "20"),
    "center": ("(W-w)/2", "(H-h)/2"),
    "bottom_left": ("20", "H-h-20"),
    "bottom_center": ("(W-w)/2", "H-h-20"),
    "bottom_right": ("W-w-20", "H-h-20"),
}


def _get_overlay_position(position: str) -> tuple[str, str]:
    """Resolve a position name to ``(x_expr, y_expr)`` for the overlay filter.

    Falls back to ``top_right`` for unrecognised names.
    """
    key = position.lower().strip().replace("-", "_").replace(" ", "_")
    if key in _POSITION_MAP:
        return _POSITION_MAP[key]
    logger.warning("Unknown position '%s', falling back to top_right", position)
    return _POSITION_MAP["top_right"]


# ── Logo overlay ─────────────────────────────────────────────────────────────


def add_logo_overlay(
    video_path: Path,
    logo_path: Path,
    position: str = "top_right",
    opacity: float = 0.8,
    output_path: Path | None = None,
    *,
    scale: float = 0.1,
) -> Path:
    """Overlay a logo image onto a video.

    The logo is scaled relative to the video width (default 10%) and placed
    at the specified position with the given opacity.  The overlay is applied
    for the full duration of the video.

    Parameters:
        video_path: Source video file.
        logo_path: Logo image file (PNG with transparency recommended).
        position: Placement -- ``"top_left"``, ``"top_right"`` (default),
            ``"bottom_left"``, ``"bottom_right"``, ``"center"``.
        opacity: Logo opacity from 0.0 (invisible) to 1.0 (fully opaque).
        output_path: Destination file.  Derived from *video_path* if ``None``.
        scale: Logo width as a fraction of the video width (default 0.1 = 10%).

    Returns:
        Path to the output video with the logo burned in.

    Raises:
        FileNotFoundError: If *video_path* or *logo_path* do not exist.
        FFmpegError: On encoding failure.
    """
    video_path = Path(video_path)
    logo_path = Path(logo_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if not logo_path.exists():
        raise FileNotFoundError(f"Logo file not found: {logo_path}")

    if output_path is None:
        output_path = video_path.with_name(f"{video_path.stem}_logo{video_path.suffix}")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    x_expr, y_expr = _get_overlay_position(position)

    logger.info(
        "Adding logo overlay: %s at %s (opacity=%.2f, scale=%.2f)",
        logo_path.name, position, opacity, scale,
    )

    # Build the filter graph
    main_video = ffmpeg.input(str(video_path))
    logo = ffmpeg.input(str(logo_path))

    # Scale the logo relative to the video width.
    # -1 for height preserves aspect ratio.
    logo_scaled = logo.filter(
        "scale",
        f"iw*{scale}/(iw/main_w)",
        -1,
    )
    # Simpler approach: scale logo to a percentage of a fixed reference.
    # We use an explicit pixel calculation instead.
    logo_scaled = logo.filter("scale", f"trunc(main_w*{scale}/2)*2", -1)

    # Apply opacity via the colorchannelmixer or format + colorize.
    # The cleanest way with overlay is to use the `format=rgba` + blend.
    if opacity < 1.0:
        # Use colorchannelmixer to adjust alpha channel
        logo_scaled = logo_scaled.filter(
            "format", "rgba",
        )
        logo_scaled = logo_scaled.filter(
            "colorchannelmixer",
            aa=opacity,
        )

    try:
        (
            ffmpeg
            .overlay(
                main_video,
                logo_scaled,
                x=x_expr,
                y=y_expr,
            )
            .output(
                str(output_path),
                vcodec="libx264",
                acodec="copy",
                crf="18",
                preset="medium",
                pix_fmt="yuv420p",
            )
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
        raise FFmpegError(f"Logo overlay failed: {stderr}") from exc

    logger.info("Logo overlay complete: %s", output_path)
    return output_path


# ── Watermark overlay ────────────────────────────────────────────────────────


def add_watermark(
    video_path: Path,
    watermark_path: Path,
    position: str = "bottom_right",
    opacity: float = 0.3,
    output_path: Path | None = None,
) -> Path:
    """Overlay a semi-transparent watermark onto a video.

    Similar to :func:`add_logo_overlay` but with defaults tuned for subtle
    watermarks (lower opacity, bottom-right placement, smaller scale).

    Parameters:
        video_path: Source video file.
        watermark_path: Watermark image file (PNG with transparency recommended).
        position: Placement position (default ``"bottom_right"``).
        opacity: Watermark opacity (default 0.3).
        output_path: Destination file.

    Returns:
        Path to the output video with the watermark burned in.

    Raises:
        FileNotFoundError: If *video_path* or *watermark_path* do not exist.
        FFmpegError: On encoding failure.
    """
    video_path = Path(video_path)
    watermark_path = Path(watermark_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if not watermark_path.exists():
        raise FileNotFoundError(f"Watermark file not found: {watermark_path}")

    if output_path is None:
        output_path = video_path.with_name(
            f"{video_path.stem}_watermark{video_path.suffix}"
        )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    x_expr, y_expr = _get_overlay_position(position)

    logger.info(
        "Adding watermark: %s at %s (opacity=%.2f)",
        watermark_path.name, position, opacity,
    )

    main_video = ffmpeg.input(str(video_path))
    watermark = ffmpeg.input(str(watermark_path))

    # Scale watermark to ~8% of video width
    watermark_scaled = watermark.filter("scale", "trunc(main_w*0.08/2)*2", -1)

    if opacity < 1.0:
        watermark_scaled = watermark_scaled.filter("format", "rgba")
        watermark_scaled = watermark_scaled.filter("colorchannelmixer", aa=opacity)

    try:
        (
            ffmpeg
            .overlay(
                main_video,
                watermark_scaled,
                x=x_expr,
                y=y_expr,
            )
            .output(
                str(output_path),
                vcodec="libx264",
                acodec="copy",
                crf="18",
                preset="medium",
                pix_fmt="yuv420p",
            )
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
        raise FFmpegError(f"Watermark overlay failed: {stderr}") from exc

    logger.info("Watermark overlay complete: %s", output_path)
    return output_path


# ── Lower third overlay ──────────────────────────────────────────────────────


def add_lower_third(
    video_path: Path,
    text: str,
    style: dict[str, Any] | None = None,
    start_time: float = 0.0,
    duration: float = 5.0,
    output_path: Path | None = None,
) -> Path:
    """Add a lower-third name/title bar overlay to a video.

    The lower third is rendered as a semi-transparent background rectangle
    with white text, appearing at *start_time* for *duration* seconds.

    Parameters:
        video_path: Source video file.
        text: The text to display in the lower third.
        style: Optional styling dict with keys:
            - ``bg_color`` (str): Background colour (default ``"black@0.7"``).
            - ``text_color`` (str): Text colour (default ``"white"``).
            - ``font`` (str): Font name (default ``"Montserrat-Bold"``).
            - ``font_size`` (int): Font size in pixels (default 36).
            - ``position`` (str): ``"bottom_left"`` (default) or
              ``"bottom_center"``.
            - ``padding`` (int): Internal padding in pixels (default 20).
            - ``margin_bottom`` (int): Bottom margin in pixels (default 80).
        start_time: When the lower third appears (seconds from start).
        duration: How long the lower third stays visible (seconds).
        output_path: Destination file.

    Returns:
        Path to the output video.

    Raises:
        FileNotFoundError: If *video_path* does not exist.
        FFmpegError: On encoding failure.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    if output_path is None:
        output_path = video_path.with_name(
            f"{video_path.stem}_lt{video_path.suffix}"
        )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    style = style or {}
    bg_color = style.get("bg_color", "black@0.7")
    text_color = style.get("text_color", "white")
    font = style.get("font", "Montserrat-Bold")
    font_size = style.get("font_size", 36)
    padding = style.get("padding", 20)
    margin_bottom = style.get("margin_bottom", 80)

    end_time = start_time + duration

    logger.info(
        "Adding lower third: '%s' at %.1f-%.1fs (font=%s, size=%d)",
        text, start_time, end_time, font, font_size,
    )

    # Escape special characters for the drawtext filter
    escaped_text = text.replace("'", "'\\''").replace(":", "\\:")

    # Build the drawtext filter expression.
    # We use enable='between(t,start,end)' to control timing.
    main_video = ffmpeg.input(str(video_path))

    # Background box + text using drawtext filter
    stream = main_video.filter(
        "drawtext",
        text=escaped_text,
        fontfile="",  # Use system font lookup
        font=font,
        fontsize=font_size,
        fontcolor=text_color,
        box=1,
        boxcolor=bg_color,
        boxborderw=padding,
        x=f"{padding + 20}",
        y=f"h-{margin_bottom}-th",
        enable=f"between(t,{start_time},{end_time})",
    )

    try:
        (
            stream
            .output(
                str(output_path),
                vcodec="libx264",
                acodec="copy",
                crf="18",
                preset="medium",
                pix_fmt="yuv420p",
            )
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
        raise FFmpegError(f"Lower third overlay failed: {stderr}") from exc

    logger.info("Lower third overlay complete: %s", output_path)
    return output_path


# ── Text overlay ─────────────────────────────────────────────────────────────


def add_text_overlay(
    video_path: Path,
    text: str,
    position: str = "center",
    font: str = "Montserrat-Bold",
    size: int = 64,
    color: str = "white",
    start_time: float = 0.0,
    duration: float = 5.0,
    output_path: Path | None = None,
    *,
    outline_color: str = "black",
    outline_width: int = 3,
) -> Path:
    """Add a timed text overlay to a video.

    Renders text at the specified position with optional outline, visible
    between *start_time* and *start_time + duration*.

    Parameters:
        video_path: Source video file.
        text: The text string to display.
        position: Placement -- ``"center"`` (default), ``"top_center"``,
            ``"bottom_center"``, etc.
        font: Font name for the text (default ``"Montserrat-Bold"``).
        size: Font size in pixels (default 64).
        color: Font colour (default ``"white"``).
        start_time: When the text appears (seconds from start).
        duration: How long the text stays visible (seconds).
        output_path: Destination file.
        outline_color: Outline / border colour (default ``"black"``).
        outline_width: Outline thickness in pixels (default 3).

    Returns:
        Path to the output video.

    Raises:
        FileNotFoundError: If *video_path* does not exist.
        FFmpegError: On encoding failure.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    if output_path is None:
        output_path = video_path.with_name(
            f"{video_path.stem}_text{video_path.suffix}"
        )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    end_time = start_time + duration

    # Map position to drawtext x/y expressions
    x_expr, y_expr = _get_text_position(position)

    logger.info(
        "Adding text overlay: '%s' at %s (%.1f-%.1fs, font=%s, size=%d)",
        text, position, start_time, end_time, font, size,
    )

    escaped_text = text.replace("'", "'\\''").replace(":", "\\:")

    main_video = ffmpeg.input(str(video_path))

    stream = main_video.filter(
        "drawtext",
        text=escaped_text,
        fontfile="",
        font=font,
        fontsize=size,
        fontcolor=color,
        borderw=outline_width,
        bordercolor=outline_color,
        x=x_expr,
        y=y_expr,
        enable=f"between(t,{start_time},{end_time})",
    )

    try:
        (
            stream
            .output(
                str(output_path),
                vcodec="libx264",
                acodec="copy",
                crf="18",
                preset="medium",
                pix_fmt="yuv420p",
            )
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
        raise FFmpegError(f"Text overlay failed: {stderr}") from exc

    logger.info("Text overlay complete: %s", output_path)
    return output_path


# ── Video concatenation (for intro/outro) ────────────────────────────────────


def concat_videos(
    video_paths: list[Path],
    output_path: Path,
) -> Path:
    """Concatenate multiple video files using the ffmpeg concat demuxer.

    All videos should have the same resolution and codec for seamless
    joining.  This is used by :class:`~aividio.brand.kit.BrandKit` to
    prepend intro and append outro videos.

    Parameters:
        video_paths: Ordered list of video file paths to concatenate.
        output_path: Destination for the concatenated video.

    Returns:
        Path to the concatenated output.

    Raises:
        ValueError: If *video_paths* is empty.
        FFmpegError: On encoding failure.
    """
    if not video_paths:
        raise ValueError("At least one video path is required for concatenation")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if len(video_paths) == 1:
        # Single file -- just copy
        import shutil
        shutil.copy2(str(video_paths[0]), str(output_path))
        return output_path

    logger.info(
        "Concatenating %d videos -> %s", len(video_paths), output_path,
    )

    # Build a concat list file
    concat_list_path = output_path.parent / f"{output_path.stem}_concat_list.txt"
    lines = [f"file '{p}'" for p in video_paths]
    concat_list_path.write_text("\n".join(lines), encoding="utf-8")

    try:
        (
            ffmpeg
            .input(str(concat_list_path), format="concat", safe=0)
            .output(
                str(output_path),
                vcodec="libx264",
                acodec="aac",
                audio_bitrate="192k",
                crf="18",
                preset="medium",
                pix_fmt="yuv420p",
                movflags="+faststart",
            )
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
        raise FFmpegError(f"Video concatenation failed: {stderr}") from exc
    finally:
        # Clean up the temporary concat list
        if concat_list_path.exists():
            concat_list_path.unlink()

    logger.info("Concatenation complete: %s", output_path)
    return output_path


# ── Internal helpers ─────────────────────────────────────────────────────────


def _get_text_position(position: str) -> tuple[str, str]:
    """Map a position name to drawtext ``(x, y)`` expressions.

    Uses text-aware centering (``tw``/``th`` = text width/height).
    """
    key = position.lower().strip().replace("-", "_").replace(" ", "_")

    text_positions: dict[str, tuple[str, str]] = {
        "top_left": ("20", "20"),
        "top_center": ("(w-tw)/2", "40"),
        "top_right": ("w-tw-20", "20"),
        "center": ("(w-tw)/2", "(h-th)/2"),
        "bottom_left": ("20", "h-th-40"),
        "bottom_center": ("(w-tw)/2", "h-th-40"),
        "bottom_right": ("w-tw-20", "h-th-40"),
    }

    if key in text_positions:
        return text_positions[key]
    logger.warning("Unknown text position '%s', falling back to center", position)
    return text_positions["center"]
