"""Caption rendering -- ASS subtitle generation and burn-in.

Supports three visual styles (legacy):
- **bold_centered**: Large centered text for TikTok / YouTube Shorts.
- **subtitle_bottom**: Traditional bottom-of-screen subtitles.
- **karaoke**: Word-by-word highlight with pop-in animation.

And 35+ animated caption templates via :func:`render_with_template`::

    from aividio.video.captions_render import render_with_template

    output = render_with_template(
        words=whisper_words,
        template_name="hormozi",
        video_path=Path("input.mp4"),
        output_path=Path("captioned.mp4"),
    )
"""

from __future__ import annotations

import logging
from pathlib import Path
from textwrap import dedent

from aividio.utils.ffmpeg import FFmpegError

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
    "highlight": {
        "font_name": "Montserrat-Bold",
        "font_size": 64,
        "primary_color": "#FFFFFF",
        "outline_color": "#000000",
        "outline_width": 4,
        "alignment": 5,
        "margin_v": 50,
        "bold": True,
        "shadow": 3,
        "highlight_color": "#10A37F",  # bright green accent for active word
    },
    "tiktok": {
        "font_name": "Montserrat-ExtraBold",
        "font_size": 72,
        "primary_color": "#FFFFFF",
        "outline_color": "#000000",
        "outline_width": 5,
        "alignment": 5,
        "margin_v": 50,
        "bold": True,
        "shadow": 3,
    },
    "minimal": {
        "font_name": "Helvetica",
        "font_size": 36,
        "primary_color": "#FFFFFF",
        "outline_color": "#333333",
        "outline_width": 1,
        "alignment": 1,  # bottom-left
        "margin_v": 40,
        "bold": False,
        "shadow": 0,
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


def _events_highlight(
    chunks: list[dict],
    highlight_color: str = "#10A37F",
) -> list[str]:
    """Word-by-word highlight -- each word lights up in *highlight_color* as
    it is spoken, then returns to the base (white) colour.

    Uses ASS ``\\kf`` tags with per-word timing.  The active word is rendered
    in the bright accent colour while all other words stay white.  This
    produces a Submagic-style "follow the bouncing ball" reading experience.
    """
    ass_highlight = _hex_to_ass_color(highlight_color)
    ass_base = _hex_to_ass_color("#FFFFFF")
    lines: list[str] = []

    for chunk in chunks:
        start = _ass_timestamp(chunk["start"])
        end = _ass_timestamp(chunk["end"])
        words = chunk["words"]
        chunk_duration = chunk["end"] - chunk["start"]

        # For each word in the chunk, we generate a separate Dialogue event
        # that shows the full chunk text but with only the current word
        # coloured in the highlight colour.
        for wi, active_word in enumerate(words):
            w_start = _ass_timestamp(active_word["start"])
            w_end = _ass_timestamp(active_word["end"])
            parts: list[str] = []

            for wj, w in enumerate(words):
                if wj == wi:
                    # Active word: bright accent colour with smooth kf fill
                    dur_cs = max(1, int(round((w["end"] - w["start"]) * 100)))
                    parts.append(
                        f"{{\\c{ass_highlight}\\kf{dur_cs}}}{w['word']}{{\\r}}"
                    )
                else:
                    # Inactive word: base (white) colour
                    parts.append(f"{{\\c{ass_base}}}{w['word']}{{\\r}}")

            text = " ".join(parts)
            lines.append(
                f"Dialogue: 0,{w_start},{w_end},Default,,0,0,0,,{text}"
            )

    return lines


def _events_bounce(chunks: list[dict]) -> list[str]:
    """Bounce/scale pop -- each chunk pops in with a scale overshoot effect.

    Scales to 120% then settles to 100% over ~150ms using ASS ``\\t``
    transform tags with ``\\fscx`` and ``\\fscy``.  This creates a satisfying
    "punch in" feel similar to Submagic's bounce preset.
    """
    lines: list[str] = []
    for chunk in chunks:
        start = _ass_timestamp(chunk["start"])
        end = _ass_timestamp(chunk["end"])
        text = chunk["text"].replace("\n", "\\N")
        # Phase 1 (0-80ms): scale from 0% to 120% overshoot
        # Phase 2 (80-150ms): settle from 120% to 100%
        bounce = (
            "{\\fscx0\\fscy0"
            "\\t(0,80,\\fscx120\\fscy120)"
            "\\t(80,150,\\fscx100\\fscy100)}"
        )
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{bounce}{text}")
    return lines


def _events_glow(chunks: list[dict]) -> list[str]:
    """Glow effect -- words appear with a bright glow/shadow that fades.

    Uses ASS shadow/border tags that animate from heavy (shadow=8, bord=6)
    to normal (shadow=2, bord=2) over 300ms.  This creates a luminous bloom
    on each chunk that settles into a clean readable state.
    """
    lines: list[str] = []
    for chunk in chunks:
        start = _ass_timestamp(chunk["start"])
        end = _ass_timestamp(chunk["end"])
        text = chunk["text"].replace("\n", "\\N")
        # Start with intense glow (large shadow + border + blur), then
        # transition to normal rendering over 300ms
        glow_effect = (
            "{\\shad8\\bord6\\blur4"
            "\\t(0,300,\\shad2\\bord2\\blur0)}"
        )
        lines.append(
            f"Dialogue: 0,{start},{end},Default,,0,0,0,,{glow_effect}{text}"
        )
    return lines


def _events_typewriter(chunks: list[dict], char_delay_ms: int = 40) -> list[str]:
    """Typewriter -- characters appear one by one from left.

    Each character fades in sequentially using per-character ``\\kf`` timing.
    Spaces are passed through without consuming a timing slot, so the reveal
    progresses smoothly across multi-word chunks.
    """
    lines: list[str] = []
    for chunk in chunks:
        start = _ass_timestamp(chunk["start"])
        end = _ass_timestamp(chunk["end"])
        full_text = chunk["text"]

        # Calculate per-character timing based on chunk duration
        char_count = sum(1 for c in full_text if c != " ")
        if char_count == 0:
            continue
        chunk_duration_cs = max(1, int(round((chunk["end"] - chunk["start"]) * 100)))
        # Distribute the chunk duration evenly across characters, but cap at
        # char_delay_ms converted to centiseconds so it doesn't drag
        per_char_cs = min(
            max(1, chunk_duration_cs // char_count),
            max(1, int(char_delay_ms / 10)),
        )

        parts: list[str] = []
        for char in full_text:
            if char == " ":
                parts.append(" ")
            else:
                parts.append(f"{{\\kf{per_char_cs}}}{char}")

        text = "".join(parts)
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
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
            ``"karaoke"``, ``"highlight"``, ``"tiktok"``, ``"minimal"``),
            a custom style dict, or ``None`` for the default.
        animation: ``"none"`` for plain text, ``"karaoke"`` for progressive
            fill, ``"pop_in"`` for scale animation, ``"highlight"`` for
            word-by-word colour highlight, ``"bounce"`` for scale overshoot
            pop-in, ``"glow"`` for bloom-to-settle shadow animation,
            ``"typewriter"`` for per-character sequential reveal.

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
    elif animation_key in ("highlight",):
        highlight_color = resolved_style.get("highlight_color", "#10A37F")
        events = _events_highlight(chunks, highlight_color=highlight_color)
    elif animation_key in ("bounce",):
        events = _events_bounce(chunks)
    elif animation_key in ("glow",):
        events = _events_glow(chunks)
    elif animation_key in ("typewriter",):
        events = _events_typewriter(chunks)
    else:
        events = _events_simple(chunks)

    content = header + "\n".join(events) + "\n"
    output_path.write_text(content, encoding="utf-8")

    logger.info("ASS file written: %s", output_path)
    return output_path


def _has_ass_filter() -> bool:
    """Check whether ffmpeg was compiled with the ``ass`` video filter (libass)."""
    import subprocess
    try:
        result = subprocess.run(
            ["ffmpeg", "-filters"],
            capture_output=True, text=True, timeout=5,
        )
        # Look for " ass " as a filter name in the output
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "ass":
                return True
        return False
    except Exception:
        return False


def _burn_captions_ass_filter(
    video_path: Path, ass_path: Path, output_path: Path
) -> None:
    """Burn ASS subtitles using ffmpeg's ``ass`` video filter (requires libass).

    Uses subprocess directly because ffmpeg-python's `.filter("ass", ...)`
    generates incorrect filter syntax for the ass filter.
    """
    import subprocess

    abs_ass = str(ass_path.resolve())
    # Escape special chars for the ffmpeg filtergraph
    escaped = (
        abs_ass
        .replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "'\\''")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", f"ass='{escaped}'",
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        str(output_path),
    ]

    logger.info("Burning captions: %s", " ".join(cmd[-4:]))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise FFmpegError(f"Caption burn-in failed: {result.stderr[-500:]}")


def _copy_without_captions(
    video_path: Path, ass_path: Path, output_path: Path
) -> None:
    """Copy the video as-is and generate a standalone SRT file alongside it.

    This is the fallback when the ``ass`` video filter is not available.
    The SRT file can be uploaded to YouTube separately or used with a player
    that supports external subtitles.
    """
    import shutil

    # Copy video without modification
    shutil.copy2(str(video_path), str(output_path))

    # Generate a companion SRT file from the ASS timestamps
    srt_path = output_path.with_suffix(".srt")
    _ass_to_srt(ass_path, srt_path)
    logger.info(
        "Video copied without burned captions. SRT file generated at %s",
        srt_path,
    )


def _ass_to_srt(ass_path: Path, srt_path: Path) -> None:
    """Convert an ASS subtitle file to SRT format for YouTube upload."""
    import re

    lines = ass_path.read_text(encoding="utf-8").splitlines()
    dialogues: list[tuple[str, str, str]] = []

    for line in lines:
        if not line.startswith("Dialogue:"):
            continue
        # Dialogue: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
        parts = line.split(",", 9)
        if len(parts) < 10:
            continue
        start_ass = parts[1].strip()
        end_ass = parts[2].strip()
        text = parts[9].strip()
        # Strip ASS override tags like {\kf100} or {\fscx0...}
        text = re.sub(r"\{[^}]*\}", "", text)
        text = text.replace("\\N", "\n").replace("\\n", "\n")
        if text.strip():
            dialogues.append((start_ass, end_ass, text))

    srt_lines: list[str] = []
    for idx, (start, end, text) in enumerate(dialogues, 1):
        srt_lines.append(str(idx))
        srt_lines.append(f"{_ass_time_to_srt(start)} --> {_ass_time_to_srt(end)}")
        srt_lines.append(text)
        srt_lines.append("")

    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")


def _ass_time_to_srt(ass_time: str) -> str:
    """Convert ASS timestamp ``H:MM:SS.cc`` to SRT ``HH:MM:SS,mmm``."""
    # ASS: 0:01:23.45  ->  SRT: 00:01:23,450
    parts = ass_time.split(":")
    if len(parts) == 3:
        h, m, s_cs = parts
        if "." in s_cs:
            s, cs = s_cs.split(".")
            ms = int(cs) * 10  # centiseconds to milliseconds
        else:
            s = s_cs
            ms = 0
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{ms:03d}"
    return ass_time  # fallback


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

    # Try ASS filter first (requires libass), fall back to soft subtitle embedding.
    if _has_ass_filter():
        _burn_captions_ass_filter(video_path, ass_path, output_path)
    else:
        logger.warning(
            "[captions] ffmpeg was not compiled with libass — "
            "embedding subtitles as a soft stream instead of burning in. "
            "Install ffmpeg with libass for hard-burned captions."
        )
        _copy_without_captions(video_path, ass_path, output_path)

    logger.info("Captioned video written: %s", output_path)
    return output_path


# ---------------------------------------------------------------------------
# Template-based animated captions (new system)
# ---------------------------------------------------------------------------

def render_with_template(
    words: list[dict],
    template_name: str,
    video_path: Path,
    output_path: Path,
    *,
    video_width: int | None = None,
    video_height: int | None = None,
    template_overrides: dict | None = None,
) -> Path:
    """Generate and burn animated captions using a named template.

    This is the high-level entry point that combines the new
    :class:`~aividio.captions.animator.CaptionAnimator` with template
    selection and ffmpeg burn-in -- replacing the basic caption workflow
    with the full Submagic-style animated version.

    Parameters:
        words: List of ``{"word": str, "start": float, "end": float}``
            dicts (typically from Whisper transcription).
        template_name: Name of a registered caption template (e.g.
            ``"hormozi"``, ``"mrbeast"``, ``"tiktok_viral"``).
        video_path: Source video file.
        output_path: Destination for the captioned video.
        video_width: Video width in pixels.  If ``None``, auto-detected
            from *video_path* via ffprobe.
        video_height: Video height in pixels.  If ``None``, auto-detected
            from *video_path* via ffprobe.
        template_overrides: Optional dict of field overrides to apply to
            the template (e.g. ``{"font_size": 72, "animation": "fade"}``).

    Returns:
        *output_path* on success.

    Raises:
        ValueError: If *words* is empty or *template_name* is unknown.
        FileNotFoundError: If *video_path* does not exist.
        FFmpegError: On ffmpeg failure.
    """
    from aividio.captions.animator import CaptionAnimator
    from aividio.captions.templates import get_template
    from aividio.utils.ffmpeg import get_resolution

    video_path = Path(video_path)
    output_path = Path(output_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Resolve video dimensions
    if video_width is None or video_height is None:
        detected_w, detected_h = get_resolution(video_path)
        video_width = video_width or detected_w
        video_height = video_height or detected_h

    # Load and optionally customise template
    template = get_template(template_name)
    if template_overrides:
        template = template.copy(**template_overrides)

    # Generate animated ASS file
    ass_path = output_path.with_suffix(".ass")
    animator = CaptionAnimator()
    animator.generate(
        words=words,
        template=template,
        video_width=video_width,
        video_height=video_height,
        output_path=ass_path,
    )

    # Burn into video
    captioned_path = burn_captions(video_path, ass_path, output_path)

    logger.info(
        "Template caption render complete: template=%s, output=%s",
        template_name,
        captioned_path,
    )
    return captioned_path


def generate_animated_ass(
    words: list[dict],
    output_path: Path,
    template_name: str = "hormozi",
    video_width: int = 1920,
    video_height: int = 1080,
    **template_overrides: object,
) -> Path:
    """Generate an animated ASS file without burning into video.

    Convenience wrapper around :class:`~aividio.captions.animator.CaptionAnimator`
    for cases where you only need the subtitle file (e.g. for preview
    or manual ffmpeg pipeline).

    Parameters:
        words: Word-level timestamps.
        output_path: Where to write the ``.ass`` file.
        template_name: Template to use.
        video_width: Target video width.
        video_height: Target video height.
        **template_overrides: Field overrides on the template.

    Returns:
        The *output_path* that was written to.
    """
    from aividio.captions.animator import CaptionAnimator
    from aividio.captions.templates import get_template

    template = get_template(template_name)
    if template_overrides:
        template = template.copy(**template_overrides)

    animator = CaptionAnimator()
    return animator.generate(
        words=words,
        template=template,
        video_width=video_width,
        video_height=video_height,
        output_path=Path(output_path),
    )
