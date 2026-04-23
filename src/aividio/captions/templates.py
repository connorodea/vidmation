"""Caption animation templates -- 35+ presets inspired by popular creators.

Each :class:`CaptionTemplate` defines every visual and behavioural property
of an animated caption overlay: typography, colours, layout, animation type,
highlight style, transition and timing.

Usage::

    from aividio.captions.templates import get_template, list_templates

    t = get_template("hormozi")
    all_names = [t["name"] for t in list_templates()]
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field, fields


@dataclass
class CaptionTemplate:
    """Complete specification for a caption animation style."""

    # -- Identity ----------------------------------------------------------
    name: str
    display_name: str
    description: str

    # -- Typography --------------------------------------------------------
    font_name: str = "Montserrat-Bold"
    font_size: int = 56  # base size; scales with resolution
    primary_color: str = "#FFFFFF"
    highlight_colors: list[str] = field(default_factory=lambda: ["#FFD700"])
    outline_color: str = "#000000"
    outline_width: int = 3
    shadow_color: str | None = "#000000"
    shadow_depth: int = 2

    # -- Layout ------------------------------------------------------------
    words_per_line: int = 3  # 1-4 words per caption group
    position: str = "center"  # center | bottom | top
    margin_bottom: int = 50  # vertical margin in pixels (PlayRes-relative)

    # -- Animation ---------------------------------------------------------
    animation: str = "none"
    # Supported: none, bounce, fade, slide_up, pop, wave, typewriter,
    #            karaoke, glow, shake
    highlight_style: str = "word_color"
    # Supported: word_color, word_bg, word_scale, word_glow, underline
    transition: str = "cut"
    # Supported: cut, crossfade, slide

    # -- Timing ------------------------------------------------------------
    word_gap_ms: int = 0  # gap between word appearances in animation

    def __post_init__(self) -> None:
        # Ensure highlight_colors is always a list
        if isinstance(self.highlight_colors, str):
            self.highlight_colors = [self.highlight_colors]

    # -- Helpers -----------------------------------------------------------

    @property
    def ass_alignment(self) -> int:
        """Map *position* to an ASS numpad alignment value."""
        return {
            "center": 5,
            "bottom": 2,
            "top": 8,
        }.get(self.position, 5)

    @property
    def ass_margin_v(self) -> int:
        """Vertical margin for ASS style line."""
        if self.position == "top":
            return 30
        return self.margin_bottom

    def copy(self, **overrides: object) -> CaptionTemplate:
        """Return a shallow copy with optional field overrides."""
        data = {f.name: getattr(self, f.name) for f in fields(self)}
        data.update(overrides)
        return CaptionTemplate(**data)


# =========================================================================
# Template registry
# =========================================================================

TEMPLATES: dict[str, CaptionTemplate] = {}


def _reg(t: CaptionTemplate) -> CaptionTemplate:
    """Register a template and return it (for convenience)."""
    TEMPLATES[t.name] = t
    return t


# ── Creator-Inspired Presets ─────────────────────────────────────────────

_reg(CaptionTemplate(
    name="hormozi",
    display_name="Hormozi",
    description="Alex Hormozi style -- bold Montserrat, gold + red word highlights, pop animation.",
    font_name="Montserrat-ExtraBold",
    font_size=56,
    primary_color="#FFFFFF",
    highlight_colors=["#FFD700", "#FF4444"],
    outline_color="#000000",
    outline_width=4,
    shadow_color="#000000",
    shadow_depth=3,
    words_per_line=2,
    position="center",
    margin_bottom=50,
    animation="pop",
    highlight_style="word_color",
    transition="cut",
    word_gap_ms=60,
))

_reg(CaptionTemplate(
    name="mrbeast",
    display_name="MrBeast",
    description="MrBeast style -- Impact font, big & colourful with bounce animation.",
    font_name="Impact",
    font_size=64,
    primary_color="#FFFFFF",
    highlight_colors=["#FF0000", "#00FF00", "#FFFF00"],
    outline_color="#000000",
    outline_width=5,
    shadow_color="#000000",
    shadow_depth=4,
    words_per_line=3,
    position="center",
    margin_bottom=50,
    animation="bounce",
    highlight_style="word_bg",
    transition="cut",
    word_gap_ms=50,
))

_reg(CaptionTemplate(
    name="ali_abdaal",
    display_name="Ali Abdaal",
    description="Ali Abdaal style -- clean sans-serif, soft blue highlight, gentle fade.",
    font_name="Inter-SemiBold",
    font_size=48,
    primary_color="#FFFFFF",
    highlight_colors=["#4A90D9", "#6EC1E4"],
    outline_color="#1A1A2E",
    outline_width=2,
    shadow_color=None,
    shadow_depth=0,
    words_per_line=3,
    position="bottom",
    margin_bottom=60,
    animation="fade",
    highlight_style="word_color",
    transition="crossfade",
    word_gap_ms=40,
))

_reg(CaptionTemplate(
    name="iman_gadzhi",
    display_name="Iman Gadzhi",
    description="Iman Gadzhi style -- bold white text, orange/red accents, pop-in.",
    font_name="Poppins-Bold",
    font_size=54,
    primary_color="#FFFFFF",
    highlight_colors=["#FF6B35", "#FF2E2E"],
    outline_color="#000000",
    outline_width=3,
    shadow_color="#1A0A00",
    shadow_depth=2,
    words_per_line=2,
    position="center",
    margin_bottom=50,
    animation="pop",
    highlight_style="word_color",
    transition="cut",
    word_gap_ms=70,
))

_reg(CaptionTemplate(
    name="garyvee",
    display_name="GaryVee",
    description="GaryVee style -- big Impact text, yellow highlight, energetic bounce.",
    font_name="Impact",
    font_size=60,
    primary_color="#FFFFFF",
    highlight_colors=["#FFDD00", "#FF3333"],
    outline_color="#000000",
    outline_width=4,
    shadow_color="#000000",
    shadow_depth=3,
    words_per_line=2,
    position="center",
    margin_bottom=45,
    animation="bounce",
    highlight_style="word_color",
    transition="cut",
    word_gap_ms=50,
))

_reg(CaptionTemplate(
    name="huberman",
    display_name="Huberman",
    description="Andrew Huberman style -- professional serif, subtle highlight, clean.",
    font_name="Georgia",
    font_size=46,
    primary_color="#FFFFFF",
    highlight_colors=["#3B82F6"],
    outline_color="#111827",
    outline_width=2,
    shadow_color=None,
    shadow_depth=0,
    words_per_line=4,
    position="bottom",
    margin_bottom=55,
    animation="fade",
    highlight_style="word_color",
    transition="crossfade",
    word_gap_ms=30,
))

_reg(CaptionTemplate(
    name="logan_paul",
    display_name="Logan Paul",
    description="Logan Paul / PRIME style -- bold, neon green highlights, shake.",
    font_name="Montserrat-Black",
    font_size=58,
    primary_color="#FFFFFF",
    highlight_colors=["#00FF88", "#00DDFF"],
    outline_color="#000000",
    outline_width=4,
    shadow_color="#003322",
    shadow_depth=3,
    words_per_line=2,
    position="center",
    margin_bottom=50,
    animation="shake",
    highlight_style="word_bg",
    transition="cut",
    word_gap_ms=60,
))

# ── Style-Based Presets ──────────────────────────────────────────────────

_reg(CaptionTemplate(
    name="minimal_white",
    display_name="Minimal White",
    description="Clean white text on dark -- no animation, minimal styling.",
    font_name="Helvetica",
    font_size=44,
    primary_color="#FFFFFF",
    highlight_colors=["#FFFFFF"],
    outline_color="#000000",
    outline_width=1,
    shadow_color=None,
    shadow_depth=0,
    words_per_line=4,
    position="bottom",
    margin_bottom=50,
    animation="none",
    highlight_style="word_color",
    transition="cut",
    word_gap_ms=0,
))

_reg(CaptionTemplate(
    name="minimal_black",
    display_name="Minimal Black",
    description="Black text on light backgrounds -- clean and readable.",
    font_name="Helvetica",
    font_size=44,
    primary_color="#1A1A1A",
    highlight_colors=["#333333"],
    outline_color="#FFFFFF",
    outline_width=1,
    shadow_color=None,
    shadow_depth=0,
    words_per_line=4,
    position="bottom",
    margin_bottom=50,
    animation="none",
    highlight_style="word_color",
    transition="cut",
    word_gap_ms=0,
))

_reg(CaptionTemplate(
    name="neon_glow",
    display_name="Neon Glow",
    description="Neon-coloured text with a bloom/glow effect.",
    font_name="Montserrat-Bold",
    font_size=52,
    primary_color="#00FFFF",
    highlight_colors=["#FF00FF", "#FFFF00", "#00FF00"],
    outline_color="#000033",
    outline_width=2,
    shadow_color="#00FFFF",
    shadow_depth=0,
    words_per_line=2,
    position="center",
    margin_bottom=50,
    animation="glow",
    highlight_style="word_glow",
    transition="crossfade",
    word_gap_ms=80,
))

_reg(CaptionTemplate(
    name="gradient_pop",
    display_name="Gradient Pop",
    description="Words pop in with cycling gradient colours.",
    font_name="Poppins-Bold",
    font_size=54,
    primary_color="#FFFFFF",
    highlight_colors=["#FF6B6B", "#4ECDC4", "#FFE66D"],
    outline_color="#000000",
    outline_width=3,
    shadow_color="#000000",
    shadow_depth=2,
    words_per_line=2,
    position="center",
    margin_bottom=50,
    animation="pop",
    highlight_style="word_color",
    transition="cut",
    word_gap_ms=70,
))

_reg(CaptionTemplate(
    name="typewriter",
    display_name="Typewriter",
    description="Characters appear one by one, typewriter-style.",
    font_name="Courier New",
    font_size=44,
    primary_color="#00FF00",
    highlight_colors=["#00FF00"],
    outline_color="#001100",
    outline_width=1,
    shadow_color=None,
    shadow_depth=0,
    words_per_line=4,
    position="bottom",
    margin_bottom=50,
    animation="typewriter",
    highlight_style="word_color",
    transition="cut",
    word_gap_ms=30,
))

_reg(CaptionTemplate(
    name="karaoke_classic",
    display_name="Karaoke Classic",
    description="Classic karaoke progressive fill -- yellow over white.",
    font_name="Arial-Bold",
    font_size=52,
    primary_color="#FFFFFF",
    highlight_colors=["#FFD700"],
    outline_color="#000000",
    outline_width=3,
    shadow_color="#000000",
    shadow_depth=2,
    words_per_line=4,
    position="bottom",
    margin_bottom=55,
    animation="karaoke",
    highlight_style="word_color",
    transition="cut",
    word_gap_ms=0,
))

_reg(CaptionTemplate(
    name="karaoke_glow",
    display_name="Karaoke Glow",
    description="Karaoke fill with glow on the active word.",
    font_name="Montserrat-Bold",
    font_size=54,
    primary_color="#FFFFFF",
    highlight_colors=["#FF6EC7"],
    outline_color="#330033",
    outline_width=2,
    shadow_color="#FF6EC7",
    shadow_depth=0,
    words_per_line=3,
    position="center",
    margin_bottom=50,
    animation="karaoke",
    highlight_style="word_glow",
    transition="crossfade",
    word_gap_ms=0,
))

_reg(CaptionTemplate(
    name="bounce_bold",
    display_name="Bounce Bold",
    description="Bold text with satisfying bounce-in animation.",
    font_name="Montserrat-ExtraBold",
    font_size=58,
    primary_color="#FFFFFF",
    highlight_colors=["#FF4444", "#44AAFF"],
    outline_color="#000000",
    outline_width=4,
    shadow_color="#000000",
    shadow_depth=3,
    words_per_line=2,
    position="center",
    margin_bottom=50,
    animation="bounce",
    highlight_style="word_color",
    transition="cut",
    word_gap_ms=60,
))

_reg(CaptionTemplate(
    name="slide_up",
    display_name="Slide Up",
    description="Words slide up from below into position.",
    font_name="Inter-Medium",
    font_size=48,
    primary_color="#FFFFFF",
    highlight_colors=["#6C5CE7"],
    outline_color="#000000",
    outline_width=2,
    shadow_color=None,
    shadow_depth=0,
    words_per_line=3,
    position="center",
    margin_bottom=50,
    animation="slide_up",
    highlight_style="word_color",
    transition="slide",
    word_gap_ms=50,
))

_reg(CaptionTemplate(
    name="wave_text",
    display_name="Wave Text",
    description="Words appear with a travelling wave-like vertical offset.",
    font_name="Poppins-SemiBold",
    font_size=50,
    primary_color="#FFFFFF",
    highlight_colors=["#00B4D8", "#0077B6"],
    outline_color="#000000",
    outline_width=2,
    shadow_color=None,
    shadow_depth=0,
    words_per_line=3,
    position="center",
    margin_bottom=50,
    animation="wave",
    highlight_style="word_color",
    transition="cut",
    word_gap_ms=80,
))

_reg(CaptionTemplate(
    name="fade_elegant",
    display_name="Fade Elegant",
    description="Elegant fade-in with crossfade transitions.",
    font_name="Playfair Display",
    font_size=46,
    primary_color="#FFFFFF",
    highlight_colors=["#C9A96E"],
    outline_color="#1A1A1A",
    outline_width=1,
    shadow_color=None,
    shadow_depth=0,
    words_per_line=4,
    position="bottom",
    margin_bottom=60,
    animation="fade",
    highlight_style="word_color",
    transition="crossfade",
    word_gap_ms=40,
))

_reg(CaptionTemplate(
    name="highlight_box",
    display_name="Highlight Box",
    description="Coloured background box behind the currently active word.",
    font_name="Montserrat-Bold",
    font_size=52,
    primary_color="#FFFFFF",
    highlight_colors=["#FF0066", "#6600FF"],
    outline_color="#000000",
    outline_width=0,
    shadow_color=None,
    shadow_depth=0,
    words_per_line=3,
    position="center",
    margin_bottom=50,
    animation="pop",
    highlight_style="word_bg",
    transition="cut",
    word_gap_ms=50,
))

_reg(CaptionTemplate(
    name="underline_slide",
    display_name="Underline Slide",
    description="Animated underline on the currently spoken word.",
    font_name="Inter-SemiBold",
    font_size=48,
    primary_color="#FFFFFF",
    highlight_colors=["#FFD700"],
    outline_color="#000000",
    outline_width=2,
    shadow_color=None,
    shadow_depth=0,
    words_per_line=3,
    position="center",
    margin_bottom=50,
    animation="fade",
    highlight_style="underline",
    transition="cut",
    word_gap_ms=40,
))

_reg(CaptionTemplate(
    name="scale_pulse",
    display_name="Scale Pulse",
    description="Current word pulses up in size then settles back.",
    font_name="Montserrat-Bold",
    font_size=52,
    primary_color="#FFFFFF",
    highlight_colors=["#FF5555", "#55FF55"],
    outline_color="#000000",
    outline_width=3,
    shadow_color="#000000",
    shadow_depth=2,
    words_per_line=2,
    position="center",
    margin_bottom=50,
    animation="pop",
    highlight_style="word_scale",
    transition="cut",
    word_gap_ms=60,
))

_reg(CaptionTemplate(
    name="color_cycle",
    display_name="Color Cycle",
    description="Words cycle through highlight colours in sequence.",
    font_name="Poppins-Bold",
    font_size=52,
    primary_color="#FFFFFF",
    highlight_colors=["#FF6B6B", "#4ECDC4", "#FFE66D", "#A78BFA"],
    outline_color="#000000",
    outline_width=3,
    shadow_color="#000000",
    shadow_depth=2,
    words_per_line=2,
    position="center",
    margin_bottom=50,
    animation="pop",
    highlight_style="word_color",
    transition="cut",
    word_gap_ms=60,
))

_reg(CaptionTemplate(
    name="shadow_depth",
    display_name="Shadow Depth",
    description="Deep, dramatic drop shadow for cinematic look.",
    font_name="Montserrat-ExtraBold",
    font_size=56,
    primary_color="#FFFFFF",
    highlight_colors=["#FFD700"],
    outline_color="#000000",
    outline_width=2,
    shadow_color="#000000",
    shadow_depth=8,
    words_per_line=3,
    position="center",
    margin_bottom=50,
    animation="fade",
    highlight_style="word_color",
    transition="cut",
    word_gap_ms=40,
))

_reg(CaptionTemplate(
    name="outline_bold",
    display_name="Outline Bold",
    description="Thick outline with no fill -- hollow text effect.",
    font_name="Impact",
    font_size=60,
    primary_color="#00000000",  # transparent fill
    highlight_colors=["#FF0000", "#00FF00"],
    outline_color="#FFFFFF",
    outline_width=6,
    shadow_color=None,
    shadow_depth=0,
    words_per_line=2,
    position="center",
    margin_bottom=50,
    animation="bounce",
    highlight_style="word_color",
    transition="cut",
    word_gap_ms=60,
))

_reg(CaptionTemplate(
    name="retro_vhs",
    display_name="Retro VHS",
    description="VHS / glitch aesthetic -- distorted, noisy feel.",
    font_name="VCR OSD Mono",
    font_size=48,
    primary_color="#FFFFFF",
    highlight_colors=["#FF0000", "#00FF00", "#0000FF"],
    outline_color="#FF0000",
    outline_width=2,
    shadow_color="#0000FF",
    shadow_depth=3,
    words_per_line=3,
    position="center",
    margin_bottom=50,
    animation="shake",
    highlight_style="word_color",
    transition="cut",
    word_gap_ms=40,
))

_reg(CaptionTemplate(
    name="cinematic",
    display_name="Cinematic",
    description="Letter-spaced thin text, bottom-center -- film subtitle feel.",
    font_name="Roboto-Light",
    font_size=40,
    primary_color="#FFFFFF",
    highlight_colors=["#CCCCCC"],
    outline_color="#000000",
    outline_width=1,
    shadow_color=None,
    shadow_depth=0,
    words_per_line=6,
    position="bottom",
    margin_bottom=40,
    animation="fade",
    highlight_style="word_color",
    transition="crossfade",
    word_gap_ms=20,
))

_reg(CaptionTemplate(
    name="documentary",
    display_name="Documentary",
    description="Lowercase, subtle, professional documentary captions.",
    font_name="Source Sans Pro",
    font_size=42,
    primary_color="#E0E0E0",
    highlight_colors=["#FFFFFF"],
    outline_color="#1A1A1A",
    outline_width=1,
    shadow_color=None,
    shadow_depth=0,
    words_per_line=5,
    position="bottom",
    margin_bottom=45,
    animation="fade",
    highlight_style="word_color",
    transition="crossfade",
    word_gap_ms=20,
))

_reg(CaptionTemplate(
    name="podcast_clean",
    display_name="Podcast Clean",
    description="Clean sans-serif with minimal animation -- podcasts and talking heads.",
    font_name="Inter-Regular",
    font_size=44,
    primary_color="#FFFFFF",
    highlight_colors=["#60A5FA"],
    outline_color="#111827",
    outline_width=2,
    shadow_color=None,
    shadow_depth=0,
    words_per_line=4,
    position="bottom",
    margin_bottom=55,
    animation="fade",
    highlight_style="word_color",
    transition="crossfade",
    word_gap_ms=30,
))

_reg(CaptionTemplate(
    name="tiktok_viral",
    display_name="TikTok Viral",
    description="Big, colourful, fast-paced -- optimised for TikTok engagement.",
    font_name="Montserrat-Black",
    font_size=62,
    primary_color="#FFFFFF",
    highlight_colors=["#FF0050", "#00F2EA", "#FFFC00"],
    outline_color="#000000",
    outline_width=4,
    shadow_color="#000000",
    shadow_depth=3,
    words_per_line=2,
    position="center",
    margin_bottom=50,
    animation="pop",
    highlight_style="word_bg",
    transition="cut",
    word_gap_ms=40,
))

_reg(CaptionTemplate(
    name="shorts_energy",
    display_name="Shorts Energy",
    description="Bold, centre-screen, high contrast -- YouTube Shorts.",
    font_name="Montserrat-ExtraBold",
    font_size=60,
    primary_color="#FFFFFF",
    highlight_colors=["#FF0000", "#FFDD00"],
    outline_color="#000000",
    outline_width=5,
    shadow_color="#000000",
    shadow_depth=3,
    words_per_line=2,
    position="center",
    margin_bottom=50,
    animation="bounce",
    highlight_style="word_color",
    transition="cut",
    word_gap_ms=50,
))

_reg(CaptionTemplate(
    name="meditation_calm",
    display_name="Meditation Calm",
    description="Thin, gentle fade, soft pastel colours -- meditation / wellness.",
    font_name="Lato-Light",
    font_size=40,
    primary_color="#E8D5B7",
    highlight_colors=["#B8A9C9"],
    outline_color="#2D2D2D",
    outline_width=1,
    shadow_color=None,
    shadow_depth=0,
    words_per_line=4,
    position="bottom",
    margin_bottom=60,
    animation="fade",
    highlight_style="word_color",
    transition="crossfade",
    word_gap_ms=60,
))

_reg(CaptionTemplate(
    name="finance_serious",
    display_name="Finance Serious",
    description="Sans-serif, white on dark, no animation -- finance / business.",
    font_name="Roboto-Medium",
    font_size=44,
    primary_color="#FFFFFF",
    highlight_colors=["#4ADE80"],
    outline_color="#0F172A",
    outline_width=2,
    shadow_color=None,
    shadow_depth=0,
    words_per_line=4,
    position="bottom",
    margin_bottom=50,
    animation="none",
    highlight_style="word_color",
    transition="cut",
    word_gap_ms=0,
))

_reg(CaptionTemplate(
    name="gaming_hype",
    display_name="Gaming Hype",
    description="Bold italic, neon colours, shake animation -- gaming content.",
    font_name="Montserrat-BoldItalic",
    font_size=58,
    primary_color="#FFFFFF",
    highlight_colors=["#00FF88", "#FF00FF", "#00DDFF"],
    outline_color="#000000",
    outline_width=4,
    shadow_color="#00FF88",
    shadow_depth=2,
    words_per_line=2,
    position="center",
    margin_bottom=50,
    animation="shake",
    highlight_style="word_glow",
    transition="cut",
    word_gap_ms=40,
))

_reg(CaptionTemplate(
    name="education_clear",
    display_name="Education Clear",
    description="Clear sans-serif with yellow highlight on key terms.",
    font_name="Open Sans SemiBold",
    font_size=46,
    primary_color="#FFFFFF",
    highlight_colors=["#FBBF24", "#F59E0B"],
    outline_color="#1E293B",
    outline_width=2,
    shadow_color=None,
    shadow_depth=0,
    words_per_line=3,
    position="bottom",
    margin_bottom=55,
    animation="fade",
    highlight_style="word_color",
    transition="crossfade",
    word_gap_ms=30,
))

_reg(CaptionTemplate(
    name="motivation_fire",
    display_name="Motivation Fire",
    description="Bold, red/orange highlights, pop animation -- motivational content.",
    font_name="Montserrat-ExtraBold",
    font_size=58,
    primary_color="#FFFFFF",
    highlight_colors=["#FF4500", "#FF6347", "#FFD700"],
    outline_color="#000000",
    outline_width=4,
    shadow_color="#331100",
    shadow_depth=3,
    words_per_line=2,
    position="center",
    margin_bottom=50,
    animation="pop",
    highlight_style="word_color",
    transition="cut",
    word_gap_ms=60,
))

_reg(CaptionTemplate(
    name="asmr_whisper",
    display_name="ASMR Whisper",
    description="Thin, gentle, soft pastel colours -- ASMR content.",
    font_name="Lato-LightItalic",
    font_size=38,
    primary_color="#D4C5A9",
    highlight_colors=["#E6B8AF", "#C4A7D7"],
    outline_color="#2C2C2C",
    outline_width=1,
    shadow_color=None,
    shadow_depth=0,
    words_per_line=4,
    position="bottom",
    margin_bottom=55,
    animation="fade",
    highlight_style="word_color",
    transition="crossfade",
    word_gap_ms=60,
))

_reg(CaptionTemplate(
    name="news_anchor",
    display_name="News Anchor",
    description="Lower-third style, professional news presentation.",
    font_name="Roboto-Bold",
    font_size=42,
    primary_color="#FFFFFF",
    highlight_colors=["#DC2626"],
    outline_color="#000000",
    outline_width=0,
    shadow_color=None,
    shadow_depth=0,
    words_per_line=5,
    position="bottom",
    margin_bottom=35,
    animation="none",
    highlight_style="word_bg",
    transition="cut",
    word_gap_ms=0,
))

_reg(CaptionTemplate(
    name="storytelling",
    display_name="Storytelling",
    description="Serif font, elegant fade transitions -- narrative content.",
    font_name="Merriweather",
    font_size=44,
    primary_color="#F5F0E1",
    highlight_colors=["#C9A96E"],
    outline_color="#1A1611",
    outline_width=1,
    shadow_color=None,
    shadow_depth=0,
    words_per_line=4,
    position="bottom",
    margin_bottom=55,
    animation="fade",
    highlight_style="word_color",
    transition="crossfade",
    word_gap_ms=40,
))

# Additional style presets

_reg(CaptionTemplate(
    name="comic_book",
    display_name="Comic Book",
    description="Bold comic-style text with colourful outlines.",
    font_name="Bangers",
    font_size=60,
    primary_color="#FFFF00",
    highlight_colors=["#FF0000", "#00AAFF"],
    outline_color="#000000",
    outline_width=5,
    shadow_color="#000000",
    shadow_depth=3,
    words_per_line=2,
    position="center",
    margin_bottom=50,
    animation="bounce",
    highlight_style="word_color",
    transition="cut",
    word_gap_ms=50,
))

_reg(CaptionTemplate(
    name="luxury_gold",
    display_name="Luxury Gold",
    description="Gold text on dark -- premium / luxury brand feel.",
    font_name="Playfair Display",
    font_size=48,
    primary_color="#D4AF37",
    highlight_colors=["#FFD700", "#FFF8DC"],
    outline_color="#1A1400",
    outline_width=1,
    shadow_color="#000000",
    shadow_depth=2,
    words_per_line=3,
    position="center",
    margin_bottom=50,
    animation="fade",
    highlight_style="word_color",
    transition="crossfade",
    word_gap_ms=50,
))

_reg(CaptionTemplate(
    name="synthwave",
    display_name="Synthwave",
    description="Retro synthwave / outrun aesthetic -- hot pink and cyan.",
    font_name="Montserrat-Bold",
    font_size=54,
    primary_color="#FF6EC7",
    highlight_colors=["#00FFFF", "#FF1493"],
    outline_color="#0D0221",
    outline_width=2,
    shadow_color="#FF6EC7",
    shadow_depth=0,
    words_per_line=2,
    position="center",
    margin_bottom=50,
    animation="glow",
    highlight_style="word_glow",
    transition="crossfade",
    word_gap_ms=70,
))

# =========================================================================
# Public API
# =========================================================================

def get_template(name: str) -> CaptionTemplate:
    """Retrieve a registered template by *name*.

    Raises
    ------
    ValueError
        If *name* is not a known template.
    """
    key = name.lower().strip().replace(" ", "_").replace("-", "_")
    if key not in TEMPLATES:
        valid = ", ".join(sorted(TEMPLATES))
        raise ValueError(f"Unknown caption template '{name}'. Valid: {valid}")
    # Return a copy so callers can mutate without affecting the registry
    return copy.deepcopy(TEMPLATES[key])


def list_templates() -> list[dict]:
    """Return a list of all registered templates as summary dicts.

    Each dict contains: ``name``, ``display_name``, ``description``,
    ``animation``, ``highlight_style``.
    """
    return [
        {
            "name": t.name,
            "display_name": t.display_name,
            "description": t.description,
            "animation": t.animation,
            "highlight_style": t.highlight_style,
            "font_name": t.font_name,
        }
        for t in TEMPLATES.values()
    ]


def create_custom_template(name: str, base: str = "hormozi", **overrides: object) -> CaptionTemplate:
    """Create a custom template by overriding fields on an existing base.

    Parameters
    ----------
    name:
        Name for the new template.
    base:
        Name of the base template to start from.
    **overrides:
        Field values to override on the base template.

    Returns
    -------
    CaptionTemplate
        A new template instance (not registered in the global registry).
    """
    base_template = get_template(base)
    overrides["name"] = name
    if "display_name" not in overrides:
        overrides["display_name"] = name.replace("_", " ").title()
    return base_template.copy(**overrides)
