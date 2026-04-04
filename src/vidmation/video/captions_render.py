"""Caption rendering -- ASS subtitle generation and burn-in.

Supports three visual styles:
- **bold_centered**: Large centered text for TikTok / YouTube Shorts.
- **subtitle_bottom**: Traditional bottom-of-screen subtitles.
- **karaoke**: Word-by-word highlight with pop-in animation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from textwrap import dedent

import ffmpeg

from vidmation.utils.ffmpeg import FFmpegError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ASS colour helpers
# ---------------------------------------------------------------------------

def _hex_to_ass_color(hex_color: str) -> str:
    """Convert ``#RRGGBB`` (or ``#RRGGBBAA``) to ASS ``&HAABBGGRR`` format."""
    h = hex_color.lstrip("#")
    if len(h) == 6:
        r, g, b = h[0:2], h[2:4], h[4:6]
        a = "00"
    elif len(h) == 8:
        r, g, b, a = h[0:2], h[2:4], h[4:6], h[6:8]
    else:
        return "&H00FFFFFF"
    return f"&H{a}{b}{g}{r}".upper()


def _ass_timestamp(seconds: float) -> str:
    """Format *seconds* as ``H:MM:SS.cc`` for ASS files."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    centiseconds = int(round((s - int(s)) * 100))
    return f"{h}:{m:02d}:{int(s):02d}.{centiseconds:02d}"


# ---------------------------------------------------------------------------
# Word chunking
# ---------------------------------------------------------------------------

def _chunk_words(
    words: list[dict],
    min_words: int = 2,
    max_words: int = 4,
    max_chars: int = 40,
) -> list[dict]:
    """Group timestamped words into display chunks.

    Each input dict must have keys ``word``, ``start``, ``end``.

    Returns a list of dicts with ``text``, ``start``, ``end``, ``words``.
    """
    chunks: list[dict] = []
    current_words: list[dict] = []

    for w in words:
        current_words.append(w)
        current_text = " ".join(cw["word"] for cw in current_words)

        at_max = len(current_words) >= max_words
        too_long = len(current_text) >= max_chars
        # Flush when we hit a natural boundary or size limit
        if at_max or too_long:
            chunks.append({
                "text": current_text,
                "start": current_words[0]["start"],
                "end": current_words[-1]["end"],
                "words": list(current_words),
            })
            current_words = []

    # Flush remainder
    if current_words:
        # Try to merge very short remainders with the previous chunk
        if chunks and len(current_words) < min_words:
            prev = chunks[-1]
            merged_text = prev["text"] + " " + " ".join(cw["word"] for cw in current_words)
            chunks[-1] = {
                "text": merged_text,
                "start": prev["start"],
                "end": current_words[-1]["end"],
                "words": prev["words"] + current_words,
            }
        else:
            chunks.append({
                "text": " ".join(cw["word"] for cw in current_words),
                "start": current_words[0]["start"],
                "end": current_words[-1]["end"],
                "words": list(current_words),
            })

    return chunks


# ---------------------------------------------------------------------------
# ASS style presets
# ---------------------------------------------------------------------------

def _build_ass_header(style: dict) -> str:
    """Build a complete ASS header with the given style parameters.

    Expected *style* keys (all optional with defaults):
    - font_name (str)
    - font_size (int)
    - primary_color (str, ``#RRGGBB``)
    - outline_color (str, ``#RRGGBB``)
    - outline_width (int)
    - alignment (int, ASS numpad alignment)
    - margin_v (int, vertical margin in pixels)
    - bold (bool)
    """
    font_name = style.get("font_name", "Montserrat-Bold")
    font_size = style.get("font_size", 48)
    primary = _hex_to_ass_color(style.get("primary_color", "#FFFFFF"))
    outline = _hex_to_ass_color(style.get("outline_color", "#000000"))
    outline_width = style.get("outline_width", 3)
    alignment = style.get("alignment", 5)  # 5 = centred middle
    margin_v = style.get("margin_v", 50)
    bold = -1 if style.get("bold", True) else 0
    shadow = style.get("shadow", 2)

    # ASS header template
    return dedent(f"""\
        [Script Info]
        Title: VIDMATION Captions
        ScriptType: v4.00+
        PlayResX: 1920
        PlayResY: 1080
        WrapStyle: 0
        ScaledBorderAndShadow: yes

        [V4+ Styles]
        Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
        Style: Default,{font_name},{font_size},{primary},&H000000FF,{outline},&H80000000,{bold},0,0,0,100,100,0,0,1,{outline_width},{shadow},{alignment},40,40,{margin_v},1

        [Events]
        Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
    """)


# ---------------------------------------------------------------------------
# Style presets
# ---------------------------------------------------------------------------

STYLE_PRESETS: dict[str, dict] = {
    "bold_centered": {
        "font_name": "Montserrat-Bold",
        "font_size": 64,
        "primary_color": "#FFFFFF",
        "outline_color": "#000000",
        "outline_width": 4,
        "alignment": 5,
        "margin_v": 50,
        "bold": True,
        "shadow": 3,
    },
    "subtitle_bottom": {
        "font_name": "Arial",
        "font_size": 42,
        "primary_color": "#FFFFFF",
        "outline_color": "#000000",
        "outline_width": 2,
        "alignment": 2,  # bottom-centre
        "margin_v": 40,
        "bold": False,
        "shadow": 1,
    },
    "karaoke": {
        "font_name": "Montserrat-Bold",
        "font_size": 58,
        "primary_color": "#FFFFFF",
        "outline_color": "#000000",
        "outline_width": 3,
        "alignment": 5,
        "margin_v": 50,
        "bold": True,
        "shadow": 2,
    },
}


def _get_style(style: dict | str | None) -> dict:
    """Resolve a style argument to a concrete style dict."""
    if style is None:
        return dict(STYLE_PRESETS["bold_centered"])
    if isinstance(style, str):
        if style in STYLE_PRESETS:
            return dict(STYLE_PRESETS[style])
        raise ValueError(f"Unknown caption style '{style}'. Valid: {list(STYLE_PRESETS)}")
    # Merge user overrides onto the bold_centered base
    merged = dict(STYLE_PRESETS["bold_centered"])
    merged.update(style)
    return merged


# ---------------------------------------------------------------------------
# ASS event generators
# ---------------------------------------------------------------------------

def _events_simple(chunks: list[dict]) -> list[str]:
    """Generate plain dialogue events (one line per chunk)."""
    lines: list[str] = []
    for chunk in chunks:
        start = _ass_timestamp(chunk["start"])
        end = _ass_timestamp(chunk["end"])
        text = chunk["text"].replace("\n", "\\N")
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
    return lines


def _events_karaoke(chunks: list[dict]) -> list[str]:
    """Generate karaoke events with word-by-word highlight (\\kf tags)."""
    lines: list[str] = []
    for chunk in chunks:
        start = _ass_timestamp(chunk["start"])
        end = _ass_timestamp(chunk["end"])
        parts: list[str] = []
        for w in chunk["words"]:
            # Duration in centiseconds for this word
            dur_cs = max(1, int(round((w["end"] - w["start"]) * 100)))
            parts.append(f"{{\\kf{dur_cs}}}{w['word']}")
        text = " ".join(parts)
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
    return lines


def _events_pop_in(chunks: list[dict]) -> list[str]:
    """Generate pop-in events using a scale animation per chunk."""
    lines: list[str] = []
    for chunk in chunks:
        start = _ass_timestamp(chunk["start"])
        end = _ass_timestamp(chunk["end"])
        text = chunk["text"].replace("\n", "\\N")
        # Pop-in: scale from 0% to 100% over 100ms
        pop = "{\\fscx0\\fscy0\\t(0,100,\\fscx100\\fscy100)}"
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{pop}{text}")
    return lines


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_ass_file(
    words: list[dict],
    output_path: Path,
    style: dict | str | None = None,
    animation: str = "none",
) -> Path:
    """Generate an ASS subtitle file from timestamped words.

    Parameters:
        words: List of dicts with ``word`` (str), ``start`` (float), ``end`` (float).
        output_path: Where to write the ``.ass`` file.
        style: A style preset name (``"bold_centered"``, ``"subtitle_bottom"``,
            ``"karaoke"``), a custom style dict, or ``None`` for the default.
        animation: ``"none"`` for plain text, ``"karaoke"`` for word-by-word
            highlight, ``"pop_in"`` for scale animation.

    Returns:
        The *output_path* that was written to.

    Raises:
        ValueError: If *words* is empty or *style*/*animation* is invalid.
    """
    if not words:
        raise ValueError("Cannot generate captions from an empty word list")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    resolved_style = _get_style(style)
    chunks = _chunk_words(words)

    logger.info(
        "Generating ASS file: %d words -> %d chunks, style=%s, animation=%s",
        len(words),
        len(chunks),
        resolved_style.get("font_name", "default"),
        animation,
    )

    header = _build_ass_header(resolved_style)

    animation_key = animation.lower().strip()
    if animation_key in ("karaoke",):
        events = _events_karaoke(chunks)
    elif animation_key in ("pop_in", "pop-in", "popin"):
        events = _events_pop_in(chunks)
    else:
        events = _events_simple(chunks)

    content = header + "\n".join(events) + "\n"
    output_path.write_text(content, encoding="utf-8")

    logger.info("ASS file written: %s", output_path)
    return output_path


def burn_captions(
    video_path: Path,
    ass_path: Path,
    output_path: Path,
) -> Path:
    """Burn ASS subtitles into a video using ffmpeg's ``ass`` filter.

    Parameters:
        video_path: Source video file.
        ass_path: The ``.ass`` subtitle file to overlay.
        output_path: Destination for the captioned video.

    Returns:
        *output_path* on success.

    Raises:
        FileNotFoundError: If *video_path* or *ass_path* do not exist.
        FFmpegError: On ffmpeg failure.
    """
    video_path = Path(video_path)
    ass_path = Path(ass_path)
    output_path = Path(output_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if not ass_path.exists():
        raise FileNotFoundError(f"ASS subtitle file not found: {ass_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Burning captions from %s into %s", ass_path.name, video_path.name)

    # The ass filter requires escaping colons and backslashes in the path.
    escaped_ass = str(ass_path).replace("\\", "\\\\").replace(":", "\\:")

    try:
        (
            ffmpeg
            .input(str(video_path))
            .filter("ass", escaped_ass)
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
        stderr = exc.stderr.decode(errors="replace") if exc.stderr else "unknown error"
        raise FFmpegError(f"Caption burn-in failed: {stderr}") from exc

    logger.info("Captioned video written: %s", output_path)
    return output_path
