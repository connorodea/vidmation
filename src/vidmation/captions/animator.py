"""CaptionAnimator -- generate animated ASS subtitle files.

This is the central engine that combines word-level timestamps from Whisper
with a :class:`~vidmation.captions.templates.CaptionTemplate` to produce a
fully animated Advanced SubStation Alpha (``.ass``) subtitle file.

The generated file can be burned into video with::

    ffmpeg -i video.mp4 -vf "ass=captions.ass" -c:a copy out.mp4

Supported animation types
-------------------------
- **none**       -- Plain text, no animation.
- **bounce**     -- Words drop in with bounce easing (overshoot + settle).
- **fade**       -- Words / groups fade in with alpha transition.
- **slide_up**   -- Words slide up from below.
- **pop**        -- Words scale from 0 % to overshoot to 100 %.
- **wave**       -- Words appear with wave-like vertical offset.
- **typewriter** -- Characters appear one by one.
- **karaoke**    -- Progressive fill colour on current word (``\\kf``).
- **glow**       -- Words pulse with glow on appearance.
- **shake**      -- Words shake on appearance for emphasis.

Supported highlight styles
--------------------------
- **word_color** -- Current word in highlight colour.
- **word_bg**    -- Coloured background box behind current word.
- **word_scale** -- Current word slightly larger.
- **word_glow**  -- Current word has glow / border-light effect.
- **underline**  -- Underline on current word.
"""

from __future__ import annotations

import logging
from pathlib import Path
from textwrap import dedent

from vidmation.captions.effects import (
    bg_highlight,
    bounce_in,
    color_highlight,
    fade_in,
    glow,
    karaoke_fill,
    pop_in,
    shake,
    slide_up,
    typewriter_char,
    underline_off,
    underline_on,
    wave_offset,
)
from vidmation.captions.templates import CaptionTemplate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Colour helpers (duplicated minimally to keep this module self-contained
# for ASS header generation)
# ---------------------------------------------------------------------------

def _hex_to_ass(hex_color: str, alpha: str = "00") -> str:
    """``#RRGGBB`` -> ASS ``&HAABBGGRR``."""
    h = hex_color.lstrip("#")
    if len(h) == 8:
        r, g, b, alpha = h[0:2], h[2:4], h[4:6], h[6:8]
    elif len(h) == 6:
        r, g, b = h[0:2], h[2:4], h[4:6]
    else:
        return "&H00FFFFFF"
    return f"&H{alpha}{b}{g}{r}".upper()


def _ass_timestamp(seconds: float) -> str:
    """Seconds -> ``H:MM:SS.cc``."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    cs = int(round((s - int(s)) * 100))
    return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"


# ---------------------------------------------------------------------------
# CaptionAnimator
# ---------------------------------------------------------------------------

class CaptionAnimator:
    """Generate ASS subtitles with advanced animations.

    Usage::

        from vidmation.captions.animator import CaptionAnimator
        from vidmation.captions.templates import get_template

        animator = CaptionAnimator()
        template = get_template("hormozi")
        ass_path = animator.generate(
            words=whisper_words,
            template=template,
            video_width=1080,
            video_height=1920,
            output_path=Path("captions.ass"),
        )
    """

    # ------------------------------------------------------------------ #
    # Public API                                                          #
    # ------------------------------------------------------------------ #

    def generate(
        self,
        words: list[dict],
        template: CaptionTemplate,
        video_width: int,
        video_height: int,
        output_path: Path,
    ) -> Path:
        """Create an animated ASS file from word timestamps and template.

        Parameters
        ----------
        words:
            List of ``{"word": str, "start": float, "end": float}`` from
            Whisper transcription.
        template:
            A :class:`CaptionTemplate` defining the visual style.
        video_width:
            Video width in pixels (used for PlayResX).
        video_height:
            Video height in pixels (used for PlayResY).
        output_path:
            Destination path for the ``.ass`` file.

        Returns
        -------
        Path
            The *output_path* that was written to.
        """
        if not words:
            raise ValueError("Cannot generate captions from an empty word list")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Scale font size relative to video resolution
        scaled_template = self._scale_template(template, video_width, video_height)

        groups = self._group_words(words, scaled_template.words_per_line)

        logger.info(
            "CaptionAnimator: %d words -> %d groups, template=%s, "
            "animation=%s, highlight=%s",
            len(words), len(groups), scaled_template.name,
            scaled_template.animation, scaled_template.highlight_style,
        )

        header = self._generate_ass_header(scaled_template, video_width, video_height)
        events = self._generate_events(groups, scaled_template)

        content = header + "\n".join(events) + "\n"
        output_path.write_text(content, encoding="utf-8")

        logger.info("Animated ASS written: %s (%d events)", output_path, len(events))
        return output_path

    # ------------------------------------------------------------------ #
    # Word grouping                                                       #
    # ------------------------------------------------------------------ #

    def _group_words(
        self,
        words: list[dict],
        words_per_line: int,
    ) -> list[dict]:
        """Group words into display chunks respecting natural phrase breaks.

        Each returned dict has:
        - ``text``  (str): joined words
        - ``start`` (float): start time of first word
        - ``end``   (float): end time of last word
        - ``words`` (list[dict]): individual word dicts
        """
        max_words = max(1, words_per_line)
        # Punctuation that signals a natural break
        break_chars = {".", ",", "!", "?", ";", ":", "--", "..."}

        chunks: list[dict] = []
        current: list[dict] = []

        for w in words:
            current.append(w)
            text = " ".join(cw["word"] for cw in current)

            at_max = len(current) >= max_words
            # Natural break: if the word ends with punctuation
            natural_break = any(w["word"].rstrip().endswith(p) for p in break_chars)
            # Character limit to avoid very long lines
            too_long = len(text) > 35

            if at_max or (natural_break and len(current) >= max(1, max_words - 1)) or too_long:
                chunks.append({
                    "text": text,
                    "start": current[0]["start"],
                    "end": current[-1]["end"],
                    "words": list(current),
                })
                current = []

        # Flush remainder
        if current:
            if chunks and len(current) == 1:
                # Merge single-word remainder with previous group
                prev = chunks[-1]
                merged = prev["words"] + current
                chunks[-1] = {
                    "text": " ".join(cw["word"] for cw in merged),
                    "start": prev["start"],
                    "end": current[-1]["end"],
                    "words": merged,
                }
            else:
                chunks.append({
                    "text": " ".join(cw["word"] for cw in current),
                    "start": current[0]["start"],
                    "end": current[-1]["end"],
                    "words": list(current),
                })

        return chunks

    # ------------------------------------------------------------------ #
    # Template scaling                                                    #
    # ------------------------------------------------------------------ #

    def _scale_template(
        self,
        template: CaptionTemplate,
        width: int,
        height: int,
    ) -> CaptionTemplate:
        """Scale font size based on video resolution.

        The base font sizes in templates assume 1080p (1920x1080).  For
        portrait / vertical video (1080x1920), we scale up slightly since
        the viewing distance tends to be closer on mobile.
        """
        # Reference resolution
        ref_height = 1080
        scale_factor = height / ref_height

        # For portrait video, boost slightly
        if height > width:
            scale_factor *= 1.05

        scaled_size = max(24, int(template.font_size * scale_factor))
        scaled_margin = max(20, int(template.margin_bottom * scale_factor))

        return template.copy(
            font_size=scaled_size,
            margin_bottom=scaled_margin,
        )

    # ------------------------------------------------------------------ #
    # ASS header                                                          #
    # ------------------------------------------------------------------ #

    def _generate_ass_header(
        self,
        template: CaptionTemplate,
        width: int,
        height: int,
    ) -> str:
        """Generate ASS header with styles derived from the template."""
        primary = _hex_to_ass(template.primary_color)
        outline = _hex_to_ass(template.outline_color)
        shadow_color = _hex_to_ass(template.shadow_color) if template.shadow_color else "&H80000000"

        # Determine bold / italic from font name heuristics
        bold = -1 if any(
            kw in template.font_name.lower()
            for kw in ("bold", "black", "extrabold", "heavy")
        ) else 0
        italic = -1 if "italic" in template.font_name.lower() else 0

        alignment = template.ass_alignment
        margin_v = template.ass_margin_v

        # Build the main Default style
        header = dedent(f"""\
            [Script Info]
            Title: VIDMATION Animated Captions
            ScriptType: v4.00+
            PlayResX: {width}
            PlayResY: {height}
            WrapStyle: 0
            ScaledBorderAndShadow: yes

            [V4+ Styles]
            Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
            Style: Default,{template.font_name},{template.font_size},{primary},&H000000FF,{outline},{shadow_color},{bold},{italic},0,0,100,100,0,0,1,{template.outline_width},{template.shadow_depth},{alignment},40,40,{margin_v},1
        """)

        # Add a Highlight style for word_bg highlight mode
        if template.highlight_style == "word_bg" and template.highlight_colors:
            bg_color = _hex_to_ass(template.highlight_colors[0])
            header += (
                f"    Style: Highlight,{template.font_name},{template.font_size},"
                f"{primary},&H000000FF,{bg_color},{bg_color},"
                f"{bold},{italic},0,0,100,100,0,0,3,{template.outline_width + 4},0,"
                f"{alignment},40,40,{margin_v},1\n"
            )

        # Add a Glow style for word_glow highlight mode
        if template.highlight_style == "word_glow" and template.highlight_colors:
            glow_color = _hex_to_ass(template.highlight_colors[0])
            header += (
                f"    Style: Glow,{template.font_name},{template.font_size},"
                f"{primary},&H000000FF,{glow_color},{glow_color},"
                f"{bold},{italic},0,0,100,100,0,0,1,{template.outline_width + 2},0,"
                f"{alignment},40,40,{margin_v},1\n"
            )

        header += dedent("""\

            [Events]
            Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        """)

        return header

    # ------------------------------------------------------------------ #
    # Event dispatch                                                      #
    # ------------------------------------------------------------------ #

    def _generate_events(
        self,
        groups: list[dict],
        template: CaptionTemplate,
    ) -> list[str]:
        """Dispatch to the appropriate event generator based on animation type."""
        animation = template.animation.lower().strip()
        dispatch = {
            "none": self._generate_simple_events,
            "bounce": self._generate_bounce_events,
            "fade": self._generate_fade_events,
            "slide_up": self._generate_slide_up_events,
            "pop": self._generate_pop_events,
            "wave": self._generate_wave_events,
            "typewriter": self._generate_typewriter_events,
            "karaoke": self._generate_karaoke_events,
            "glow": self._generate_glow_events,
            "shake": self._generate_shake_events,
        }
        generator = dispatch.get(animation, self._generate_simple_events)
        return generator(groups, template)

    # ------------------------------------------------------------------ #
    # Simple (no animation)                                               #
    # ------------------------------------------------------------------ #

    def _generate_simple_events(
        self,
        groups: list[dict],
        template: CaptionTemplate,
    ) -> list[str]:
        """Plain dialogue events with optional word highlighting."""
        lines: list[str] = []
        for group in groups:
            start = _ass_timestamp(group["start"])
            end = _ass_timestamp(group["end"])
            text = self._apply_highlight(group, template)
            lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
        return lines

    # ------------------------------------------------------------------ #
    # Bounce animation                                                    #
    # ------------------------------------------------------------------ #

    def _generate_bounce_events(
        self,
        groups: list[dict],
        template: CaptionTemplate,
    ) -> list[str]:
        """Words drop in with bounce easing.

        Each word in the group gets a staggered bounce-in, creating a
        cascading drop effect.
        """
        lines: list[str] = []
        for group in groups:
            start = _ass_timestamp(group["start"])
            end = _ass_timestamp(group["end"])
            words = group["words"]
            parts: list[str] = []

            for i, w in enumerate(words):
                delay = i * template.word_gap_ms
                effect = bounce_in(delay_ms=delay, duration_ms=300)
                word_text = self._highlight_word(
                    w["word"], i, len(words), template,
                )
                parts.append(f"{effect}{word_text}")

            text = " ".join(parts)
            # Add crossfade transition if specified
            if template.transition == "crossfade":
                text = fade_in(150, 100) + text
            lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
        return lines

    # ------------------------------------------------------------------ #
    # Pop animation                                                       #
    # ------------------------------------------------------------------ #

    def _generate_pop_events(
        self,
        groups: list[dict],
        template: CaptionTemplate,
    ) -> list[str]:
        """Words scale from 0 to overshoot to 100 % with punchy feel."""
        lines: list[str] = []
        for group in groups:
            start = _ass_timestamp(group["start"])
            end = _ass_timestamp(group["end"])
            words = group["words"]

            if len(words) == 1:
                # Single word: animate the whole group
                effect = pop_in(delay_ms=0, duration_ms=250)
                word_text = self._highlight_word(
                    words[0]["word"], 0, 1, template,
                )
                text = f"{effect}{word_text}"
            else:
                parts: list[str] = []
                for i, w in enumerate(words):
                    delay = i * template.word_gap_ms
                    effect = pop_in(delay_ms=delay, duration_ms=250)
                    word_text = self._highlight_word(
                        w["word"], i, len(words), template,
                    )
                    parts.append(f"{effect}{word_text}")
                text = " ".join(parts)

            if template.transition == "crossfade":
                text = fade_in(120, 80) + text
            lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
        return lines

    # ------------------------------------------------------------------ #
    # Fade animation                                                      #
    # ------------------------------------------------------------------ #

    def _generate_fade_events(
        self,
        groups: list[dict],
        template: CaptionTemplate,
    ) -> list[str]:
        """Groups fade in with alpha transition."""
        lines: list[str] = []
        for group in groups:
            start = _ass_timestamp(group["start"])
            end = _ass_timestamp(group["end"])

            fade_out_ms = 100 if template.transition == "crossfade" else 0
            effect = fade_in(duration_ms=250, fade_out_ms=fade_out_ms)
            text = self._apply_highlight(group, template)
            lines.append(
                f"Dialogue: 0,{start},{end},Default,,0,0,0,,{effect}{text}"
            )
        return lines

    # ------------------------------------------------------------------ #
    # Slide-up animation                                                  #
    # ------------------------------------------------------------------ #

    def _generate_slide_up_events(
        self,
        groups: list[dict],
        template: CaptionTemplate,
    ) -> list[str]:
        """Words slide up from below into final position."""
        lines: list[str] = []
        for group in groups:
            start = _ass_timestamp(group["start"])
            end = _ass_timestamp(group["end"])

            effect = slide_up(distance=40, duration_ms=300, delay_ms=0)
            text = self._apply_highlight(group, template)
            lines.append(
                f"Dialogue: 0,{start},{end},Default,,0,0,0,,{effect}{text}"
            )
        return lines

    # ------------------------------------------------------------------ #
    # Wave animation                                                      #
    # ------------------------------------------------------------------ #

    def _generate_wave_events(
        self,
        groups: list[dict],
        template: CaptionTemplate,
    ) -> list[str]:
        """Words appear with wave-like vertical offset."""
        lines: list[str] = []
        for group in groups:
            start = _ass_timestamp(group["start"])
            end = _ass_timestamp(group["end"])
            words = group["words"]
            parts: list[str] = []

            for i, w in enumerate(words):
                effect = wave_offset(
                    word_index=i,
                    amplitude=8,
                    wave_speed_ms=template.word_gap_ms or 80,
                )
                word_text = self._highlight_word(
                    w["word"], i, len(words), template,
                )
                parts.append(f"{effect}{word_text}")

            text = " ".join(parts)
            if template.transition == "crossfade":
                text = fade_in(150, 100) + text
            lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
        return lines

    # ------------------------------------------------------------------ #
    # Typewriter animation                                                #
    # ------------------------------------------------------------------ #

    def _generate_typewriter_events(
        self,
        groups: list[dict],
        template: CaptionTemplate,
    ) -> list[str]:
        """Characters appear one by one, typewriter-style."""
        lines: list[str] = []
        char_delay = template.word_gap_ms or 30

        for group in groups:
            start = _ass_timestamp(group["start"])
            end = _ass_timestamp(group["end"])
            full_text = group["text"]
            parts: list[str] = []

            char_idx = 0
            for char in full_text:
                if char == " ":
                    parts.append(" ")
                else:
                    effect = typewriter_char(char_idx, char_delay)
                    parts.append(f"{effect}{char}")
                    char_idx += 1

            text = "".join(parts)
            lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
        return lines

    # ------------------------------------------------------------------ #
    # Karaoke animation                                                   #
    # ------------------------------------------------------------------ #

    def _generate_karaoke_events(
        self,
        groups: list[dict],
        template: CaptionTemplate,
    ) -> list[str]:
        """Progressive fill colour on current word (\\kf tag).

        The secondary colour (set in ASS style) fills over the primary
        colour as each word is spoken.
        """
        lines: list[str] = []
        for group in groups:
            start = _ass_timestamp(group["start"])
            end = _ass_timestamp(group["end"])
            words = group["words"]
            parts: list[str] = []

            # Set the karaoke fill colour
            if template.highlight_colors:
                fill_color = _hex_to_ass(template.highlight_colors[0])
                parts.append(f"{{\\1c{fill_color}}}")

            for w in words:
                duration_cs = max(1, int(round((w["end"] - w["start"]) * 100)))
                parts.append(karaoke_fill(duration_cs) + w["word"])

            text = " ".join(parts)

            # Use Glow style if word_glow highlight is active
            style = "Glow" if template.highlight_style == "word_glow" else "Default"
            lines.append(f"Dialogue: 0,{start},{end},{style},,0,0,0,,{text}")
        return lines

    # ------------------------------------------------------------------ #
    # Glow animation                                                      #
    # ------------------------------------------------------------------ #

    def _generate_glow_events(
        self,
        groups: list[dict],
        template: CaptionTemplate,
    ) -> list[str]:
        """Words pulse with glow on appearance."""
        lines: list[str] = []
        for group in groups:
            start = _ass_timestamp(group["start"])
            end = _ass_timestamp(group["end"])
            words = group["words"]
            parts: list[str] = []

            glow_color = template.highlight_colors[0] if template.highlight_colors else "#FFFFFF"

            for i, w in enumerate(words):
                delay = i * (template.word_gap_ms or 80)
                # Glow in, then settle to normal outline
                glow_effect = glow(color=glow_color, blur=8, strength=4)
                pop_effect = pop_in(delay_ms=delay, duration_ms=250)
                word_text = self._highlight_word(
                    w["word"], i, len(words), template,
                )
                # Combine: pop in with glow, then transition glow to normal
                ass_glow_color = _hex_to_ass(glow_color)
                settle = (
                    f"{{\\t({delay + 250},{delay + 500},"
                    f"\\3c{_hex_to_ass(template.outline_color)}\\blur0\\bord{template.outline_width})}}"
                )
                parts.append(f"{glow_effect}{pop_effect}{word_text}{settle}")

            text = " ".join(parts)
            if template.transition == "crossfade":
                text = fade_in(150, 100) + text
            lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
        return lines

    # ------------------------------------------------------------------ #
    # Shake animation                                                     #
    # ------------------------------------------------------------------ #

    def _generate_shake_events(
        self,
        groups: list[dict],
        template: CaptionTemplate,
    ) -> list[str]:
        """Words shake on appearance for emphasis."""
        lines: list[str] = []
        for group in groups:
            start = _ass_timestamp(group["start"])
            end = _ass_timestamp(group["end"])
            words = group["words"]
            parts: list[str] = []

            for i, w in enumerate(words):
                delay = i * (template.word_gap_ms or 40)
                shake_effect = shake(intensity=3, duration_ms=200, delay_ms=delay)
                pop_effect = pop_in(delay_ms=delay, duration_ms=200)
                word_text = self._highlight_word(
                    w["word"], i, len(words), template,
                )
                parts.append(f"{pop_effect}{shake_effect}{word_text}")

            text = " ".join(parts)
            lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
        return lines

    # ------------------------------------------------------------------ #
    # Word highlighting                                                   #
    # ------------------------------------------------------------------ #

    def _highlight_word(
        self,
        word: str,
        word_index: int,
        total_words: int,
        template: CaptionTemplate,
    ) -> str:
        """Apply highlight style to an individual word based on its index.

        The *last* word in each group is treated as the "active" word.
        For word_color: the active word gets the highlight colour.
        """
        if not template.highlight_colors:
            return word

        style = template.highlight_style
        colors = template.highlight_colors

        # The "active" word is the last one (most recently spoken)
        is_active = word_index == total_words - 1

        if style == "word_color" and is_active:
            color = colors[word_index % len(colors)]
            return color_highlight(word, color)

        if style == "word_bg" and is_active:
            color = colors[word_index % len(colors)]
            return bg_highlight(word, color, padding=10)

        if style == "word_scale" and is_active:
            return f"{{\\fscx115\\fscy115}}{word}{{\\r}}"

        if style == "word_glow" and is_active:
            glow_color = colors[word_index % len(colors)]
            glow_effect = glow(color=glow_color, blur=6, strength=3)
            return f"{glow_effect}{word}{{\\r}}"

        if style == "underline" and is_active:
            ul_color = colors[word_index % len(colors)]
            return f"{underline_on(ul_color)}{word}{underline_off()}"

        return word

    def _apply_highlight(
        self,
        group: dict,
        template: CaptionTemplate,
    ) -> str:
        """Apply word highlighting across an entire group.

        For groups displayed as a unit (no per-word animation), this
        highlights each word individually and joins them.
        """
        words = group["words"]
        if not template.highlight_colors or template.highlight_style == "word_color":
            # For word_color with no per-word animation, highlight each word
            # with cycling colours
            if template.highlight_colors and len(template.highlight_colors) > 0:
                parts: list[str] = []
                for i, w in enumerate(words):
                    is_last = i == len(words) - 1
                    if is_last:
                        color = template.highlight_colors[i % len(template.highlight_colors)]
                        parts.append(color_highlight(w["word"], color))
                    else:
                        parts.append(w["word"])
                return " ".join(parts)
            return group["text"]

        # For other highlight styles, use the per-word highlighter
        parts = []
        for i, w in enumerate(words):
            parts.append(
                self._highlight_word(w["word"], i, len(words), template)
            )
        return " ".join(parts)
