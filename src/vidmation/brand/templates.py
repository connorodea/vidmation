"""Video template system -- pre-defined visual recipes for common video styles.

A :class:`VideoTemplate` defines the structural and aesthetic blueprint for a
video: how many sections, what visual style each section uses, transition type,
music genre, caption preset, and colour scheme.  Templates are composable with
:class:`~vidmation.brand.kit.BrandKit` for full brand consistency.

Built-in templates cover the most popular faceless YouTube niches.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from vidmation.models.video import VideoFormat

logger = logging.getLogger(__name__)


# ── Section specification ────────────────────────────────────────────────────


@dataclass
class TemplateSectionSpec:
    """Specification for a single section within a video template.

    Attributes:
        section_type: Semantic role -- ``"hook"``, ``"content"``, ``"cta"``,
            ``"intro"``, ``"outro"``, ``"transition"``.
        duration_range: ``(min_seconds, max_seconds)`` for this section.
        visual_style: Descriptor for the image/video generation prompt
            (e.g. ``"dramatic_zoom"``, ``"text_on_screen"``, ``"b_roll"``).
        caption_style: ASS caption preset name or custom dict.
        description: Human-readable purpose of this section.
    """

    section_type: str  # hook | content | cta | intro | outro | transition
    duration_range: tuple[float, float] = (5.0, 15.0)
    visual_style: str = "b_roll"
    caption_style: str = "bold_centered"
    description: str = ""


# ── Video template ───────────────────────────────────────────────────────────


@dataclass
class VideoTemplate:
    """Blueprint for a complete video's structure and aesthetics.

    Templates define the creative direction without binding to specific content.
    They pair with a :class:`~vidmation.brand.kit.BrandKit` for full branding.

    Attributes:
        name: Unique identifier / slug (e.g. ``"listicle_dark"``).
        description: Human-readable description of the template style.
        format: Target video format (landscape, portrait, short).
        sections: Ordered list of :class:`TemplateSectionSpec` defining the
            video's structure.
        transition_style: Default transition between sections.
        music_genre: Suggested background music genre.
        caption_preset: Default caption visual preset name.
        color_scheme: Dict of named colours used by the template's prompts
            and overlays.
        pacing: General pacing descriptor -- ``"fast"``, ``"medium"``,
            ``"slow"``.
        target_duration_range: ``(min, max)`` total video duration in seconds.
        tags: Metadata tags for template discovery / filtering.
    """

    name: str
    description: str = ""
    format: VideoFormat = VideoFormat.LANDSCAPE
    sections: list[TemplateSectionSpec] = field(default_factory=list)
    transition_style: str = "crossfade"
    music_genre: str = "ambient"
    caption_preset: str = "bold_centered"
    color_scheme: dict[str, str] = field(default_factory=dict)
    pacing: str = "medium"
    target_duration_range: tuple[float, float] = (480.0, 900.0)
    tags: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @property
    def total_min_duration(self) -> float:
        """Sum of all section minimum durations."""
        return sum(s.duration_range[0] for s in self.sections)

    @property
    def total_max_duration(self) -> float:
        """Sum of all section maximum durations."""
        return sum(s.duration_range[1] for s in self.sections)

    @property
    def section_count(self) -> int:
        """Number of sections in this template."""
        return len(self.sections)

    def get_sections_by_type(self, section_type: str) -> list[TemplateSectionSpec]:
        """Return all sections matching *section_type*."""
        return [s for s in self.sections if s.section_type == section_type]

    def to_dict(self) -> dict[str, Any]:
        """Serialise the template to a plain dict (YAML-friendly)."""
        return {
            "name": self.name,
            "description": self.description,
            "format": self.format.value,
            "sections": [
                {
                    "section_type": s.section_type,
                    "duration_range": list(s.duration_range),
                    "visual_style": s.visual_style,
                    "caption_style": s.caption_style,
                    "description": s.description,
                }
                for s in self.sections
            ],
            "transition_style": self.transition_style,
            "music_genre": self.music_genre,
            "caption_preset": self.caption_preset,
            "color_scheme": dict(self.color_scheme),
            "pacing": self.pacing,
            "target_duration_range": list(self.target_duration_range),
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VideoTemplate:
        """Deserialise a template from a plain dict.

        Parameters:
            data: Dict with keys matching :class:`VideoTemplate` fields.

        Returns:
            A populated :class:`VideoTemplate`.
        """
        sections = [
            TemplateSectionSpec(
                section_type=s["section_type"],
                duration_range=tuple(s.get("duration_range", (5.0, 15.0))),
                visual_style=s.get("visual_style", "b_roll"),
                caption_style=s.get("caption_style", "bold_centered"),
                description=s.get("description", ""),
            )
            for s in data.get("sections", [])
        ]

        fmt_str = data.get("format", "landscape")
        try:
            fmt = VideoFormat(fmt_str)
        except ValueError:
            fmt = VideoFormat.LANDSCAPE

        dur_range = data.get("target_duration_range", [480.0, 900.0])

        return cls(
            name=data["name"],
            description=data.get("description", ""),
            format=fmt,
            sections=sections,
            transition_style=data.get("transition_style", "crossfade"),
            music_genre=data.get("music_genre", "ambient"),
            caption_preset=data.get("caption_preset", "bold_centered"),
            color_scheme=data.get("color_scheme", {}),
            pacing=data.get("pacing", "medium"),
            target_duration_range=(dur_range[0], dur_range[1]),
            tags=data.get("tags", []),
        )

    def __repr__(self) -> str:
        return (
            f"<VideoTemplate '{self.name}' "
            f"({self.format.value}, {self.section_count} sections, "
            f"{self.pacing} pacing)>"
        )


# ── Built-in templates ───────────────────────────────────────────────────────

BUILT_IN_TEMPLATES: dict[str, VideoTemplate] = {

    # -- Listicle Dark ---------------------------------------------------------
    "listicle_dark": VideoTemplate(
        name="listicle_dark",
        description=(
            "Dark-themed listicle with numbered sections, bold captions, and "
            "dramatic transitions. Ideal for top-10 / ranked content."
        ),
        format=VideoFormat.LANDSCAPE,
        sections=[
            TemplateSectionSpec(
                section_type="hook",
                duration_range=(5.0, 10.0),
                visual_style="dramatic_zoom",
                caption_style="bold_centered",
                description="Attention-grabbing hook with bold question or statement",
            ),
            TemplateSectionSpec(
                section_type="content",
                duration_range=(30.0, 60.0),
                visual_style="numbered_overlay",
                caption_style="bold_centered",
                description="Numbered list item with B-roll and text overlay",
            ),
            TemplateSectionSpec(
                section_type="content",
                duration_range=(30.0, 60.0),
                visual_style="numbered_overlay",
                caption_style="bold_centered",
                description="Numbered list item with B-roll and text overlay",
            ),
            TemplateSectionSpec(
                section_type="content",
                duration_range=(30.0, 60.0),
                visual_style="numbered_overlay",
                caption_style="bold_centered",
                description="Numbered list item with B-roll and text overlay",
            ),
            TemplateSectionSpec(
                section_type="content",
                duration_range=(30.0, 60.0),
                visual_style="numbered_overlay",
                caption_style="bold_centered",
                description="Numbered list item with B-roll and text overlay",
            ),
            TemplateSectionSpec(
                section_type="content",
                duration_range=(30.0, 60.0),
                visual_style="numbered_overlay",
                caption_style="bold_centered",
                description="Numbered list item with B-roll and text overlay",
            ),
            TemplateSectionSpec(
                section_type="cta",
                duration_range=(10.0, 20.0),
                visual_style="subscribe_prompt",
                caption_style="bold_centered",
                description="Call to action: subscribe, like, comment",
            ),
        ],
        transition_style="crossfade",
        music_genre="dark_cinematic",
        caption_preset="bold_centered",
        color_scheme={
            "primary": "#FF4444",
            "secondary": "#1A1A2E",
            "accent": "#E94560",
            "background": "#0F0F23",
            "text": "#FFFFFF",
            "number_highlight": "#FF4444",
        },
        pacing="medium",
        target_duration_range=(480.0, 900.0),
        tags=["listicle", "top10", "ranked", "dark"],
    ),

    # -- Educational Clean -----------------------------------------------------
    "educational_clean": VideoTemplate(
        name="educational_clean",
        description=(
            "Clean, professional educational style with a white/light colour "
            "palette, diagram-style visuals, and subtle bottom captions."
        ),
        format=VideoFormat.LANDSCAPE,
        sections=[
            TemplateSectionSpec(
                section_type="hook",
                duration_range=(5.0, 10.0),
                visual_style="question_card",
                caption_style="subtitle_bottom",
                description="Opening question or curiosity hook",
            ),
            TemplateSectionSpec(
                section_type="intro",
                duration_range=(10.0, 20.0),
                visual_style="topic_overview",
                caption_style="subtitle_bottom",
                description="Brief overview of what will be covered",
            ),
            TemplateSectionSpec(
                section_type="content",
                duration_range=(60.0, 120.0),
                visual_style="diagram_explanation",
                caption_style="subtitle_bottom",
                description="Main educational content with visual aids",
            ),
            TemplateSectionSpec(
                section_type="content",
                duration_range=(60.0, 120.0),
                visual_style="diagram_explanation",
                caption_style="subtitle_bottom",
                description="Deeper dive into the topic",
            ),
            TemplateSectionSpec(
                section_type="content",
                duration_range=(30.0, 60.0),
                visual_style="example_showcase",
                caption_style="subtitle_bottom",
                description="Real-world example or case study",
            ),
            TemplateSectionSpec(
                section_type="cta",
                duration_range=(10.0, 15.0),
                visual_style="summary_card",
                caption_style="subtitle_bottom",
                description="Summary and gentle call to action",
            ),
        ],
        transition_style="crossfade",
        music_genre="soft_piano",
        caption_preset="subtitle_bottom",
        color_scheme={
            "primary": "#2196F3",
            "secondary": "#F5F5F5",
            "accent": "#4CAF50",
            "background": "#FFFFFF",
            "text": "#333333",
            "diagram_accent": "#FF9800",
        },
        pacing="medium",
        target_duration_range=(480.0, 900.0),
        tags=["educational", "clean", "explainer", "tutorial"],
    ),

    # -- Storytelling Cinematic ------------------------------------------------
    "storytelling_cinematic": VideoTemplate(
        name="storytelling_cinematic",
        description=(
            "Cinematic widescreen storytelling with dramatic music, film grain, "
            "and letterbox bars. Perfect for narrative and documentary content."
        ),
        format=VideoFormat.LANDSCAPE,
        sections=[
            TemplateSectionSpec(
                section_type="hook",
                duration_range=(8.0, 15.0),
                visual_style="cinematic_opening",
                caption_style="subtitle_bottom",
                description="Atmospheric opening shot with dramatic narration",
            ),
            TemplateSectionSpec(
                section_type="content",
                duration_range=(60.0, 120.0),
                visual_style="cinematic_b_roll",
                caption_style="subtitle_bottom",
                description="Story setup and context building",
            ),
            TemplateSectionSpec(
                section_type="content",
                duration_range=(90.0, 180.0),
                visual_style="cinematic_b_roll",
                caption_style="subtitle_bottom",
                description="Rising action / main narrative arc",
            ),
            TemplateSectionSpec(
                section_type="content",
                duration_range=(60.0, 120.0),
                visual_style="cinematic_b_roll",
                caption_style="subtitle_bottom",
                description="Climax and resolution",
            ),
            TemplateSectionSpec(
                section_type="cta",
                duration_range=(10.0, 20.0),
                visual_style="cinematic_closing",
                caption_style="subtitle_bottom",
                description="Reflective outro with soft call to action",
            ),
        ],
        transition_style="fade_black",
        music_genre="cinematic_orchestral",
        caption_preset="subtitle_bottom",
        color_scheme={
            "primary": "#D4AF37",
            "secondary": "#1C1C1C",
            "accent": "#8B7355",
            "background": "#0A0A0A",
            "text": "#E8E8E8",
            "film_grain": "light",
        },
        pacing="slow",
        target_duration_range=(600.0, 1200.0),
        tags=["storytelling", "cinematic", "documentary", "narrative"],
    ),

    # -- Shorts Viral ----------------------------------------------------------
    "shorts_viral": VideoTemplate(
        name="shorts_viral",
        description=(
            "Rapid-fire vertical format for YouTube Shorts / TikTok / Reels. "
            "Fast cuts, huge text, trending music style. Maximum engagement "
            "in under 60 seconds."
        ),
        format=VideoFormat.SHORT,
        sections=[
            TemplateSectionSpec(
                section_type="hook",
                duration_range=(2.0, 4.0),
                visual_style="big_text_reveal",
                caption_style="bold_centered",
                description="Immediate hook -- bold text or shocking statement",
            ),
            TemplateSectionSpec(
                section_type="content",
                duration_range=(8.0, 15.0),
                visual_style="fast_cut_montage",
                caption_style="bold_centered",
                description="Quick-fire content delivery with rapid transitions",
            ),
            TemplateSectionSpec(
                section_type="content",
                duration_range=(8.0, 15.0),
                visual_style="fast_cut_montage",
                caption_style="bold_centered",
                description="Continuation with visual variety",
            ),
            TemplateSectionSpec(
                section_type="content",
                duration_range=(8.0, 15.0),
                visual_style="fast_cut_montage",
                caption_style="bold_centered",
                description="Payoff or reveal",
            ),
            TemplateSectionSpec(
                section_type="cta",
                duration_range=(3.0, 5.0),
                visual_style="follow_prompt",
                caption_style="bold_centered",
                description="Quick follow / like prompt",
            ),
        ],
        transition_style="cut",
        music_genre="trending_pop",
        caption_preset="bold_centered",
        color_scheme={
            "primary": "#FF0050",
            "secondary": "#00F2EA",
            "accent": "#FFFC00",
            "background": "#000000",
            "text": "#FFFFFF",
        },
        pacing="fast",
        target_duration_range=(30.0, 58.0),
        tags=["shorts", "viral", "tiktok", "reels", "fast"],
    ),

    # -- Meditation Calm -------------------------------------------------------
    "meditation_calm": VideoTemplate(
        name="meditation_calm",
        description=(
            "Slow, calming content with nature footage, soft voice narration, "
            "gentle transitions, and minimalist text. Perfect for meditation, "
            "relaxation, and ambient channels."
        ),
        format=VideoFormat.LANDSCAPE,
        sections=[
            TemplateSectionSpec(
                section_type="intro",
                duration_range=(15.0, 30.0),
                visual_style="nature_slow_motion",
                caption_style="subtitle_bottom",
                description="Gentle welcome and settling in",
            ),
            TemplateSectionSpec(
                section_type="content",
                duration_range=(120.0, 300.0),
                visual_style="nature_slow_motion",
                caption_style="subtitle_bottom",
                description="Main meditation / relaxation content",
            ),
            TemplateSectionSpec(
                section_type="content",
                duration_range=(120.0, 300.0),
                visual_style="nature_ambient",
                caption_style="subtitle_bottom",
                description="Deep relaxation phase",
            ),
            TemplateSectionSpec(
                section_type="cta",
                duration_range=(10.0, 20.0),
                visual_style="gentle_fade",
                caption_style="subtitle_bottom",
                description="Soft closing and gentle CTA",
            ),
        ],
        transition_style="fade_black",
        music_genre="ambient_nature",
        caption_preset="subtitle_bottom",
        color_scheme={
            "primary": "#7CB9A8",
            "secondary": "#F0EDE5",
            "accent": "#A8D5BA",
            "background": "#1B2A2A",
            "text": "#E8E8E8",
        },
        pacing="slow",
        target_duration_range=(600.0, 3600.0),
        tags=["meditation", "calm", "relaxation", "ambient", "nature"],
    ),

    # -- Finance Serious -------------------------------------------------------
    "finance_serious": VideoTemplate(
        name="finance_serious",
        description=(
            "Authoritative dark-themed finance content with data overlays, "
            "chart-style visuals, and a professional tone. For stock market, "
            "crypto, and personal finance channels."
        ),
        format=VideoFormat.LANDSCAPE,
        sections=[
            TemplateSectionSpec(
                section_type="hook",
                duration_range=(5.0, 10.0),
                visual_style="data_reveal",
                caption_style="bold_centered",
                description="Attention-grabbing financial claim or headline",
            ),
            TemplateSectionSpec(
                section_type="intro",
                duration_range=(10.0, 20.0),
                visual_style="market_overview",
                caption_style="subtitle_bottom",
                description="Context setting with market backdrop",
            ),
            TemplateSectionSpec(
                section_type="content",
                duration_range=(60.0, 120.0),
                visual_style="chart_analysis",
                caption_style="subtitle_bottom",
                description="Data-driven analysis with chart visuals",
            ),
            TemplateSectionSpec(
                section_type="content",
                duration_range=(60.0, 120.0),
                visual_style="data_comparison",
                caption_style="subtitle_bottom",
                description="Comparative analysis or deep dive",
            ),
            TemplateSectionSpec(
                section_type="content",
                duration_range=(30.0, 60.0),
                visual_style="expert_insight",
                caption_style="subtitle_bottom",
                description="Expert-level takeaways and predictions",
            ),
            TemplateSectionSpec(
                section_type="cta",
                duration_range=(10.0, 20.0),
                visual_style="summary_card",
                caption_style="bold_centered",
                description="Summary and call to action",
            ),
        ],
        transition_style="crossfade",
        music_genre="corporate_tense",
        caption_preset="subtitle_bottom",
        color_scheme={
            "primary": "#00C853",
            "secondary": "#1A1A2E",
            "accent": "#FF1744",
            "background": "#0D1117",
            "text": "#E6E6E6",
            "positive": "#00C853",
            "negative": "#FF1744",
        },
        pacing="medium",
        target_duration_range=(480.0, 900.0),
        tags=["finance", "stocks", "crypto", "business", "data"],
    ),

    # -- Tech Modern -----------------------------------------------------------
    "tech_modern": VideoTemplate(
        name="tech_modern",
        description=(
            "Futuristic tech aesthetic with neon accents, code snippets, "
            "glitch transitions, and a modern electronic soundtrack. For "
            "tech reviews, programming, and AI content."
        ),
        format=VideoFormat.LANDSCAPE,
        sections=[
            TemplateSectionSpec(
                section_type="hook",
                duration_range=(5.0, 10.0),
                visual_style="neon_text_reveal",
                caption_style="bold_centered",
                description="High-energy tech hook with glitch effects",
            ),
            TemplateSectionSpec(
                section_type="intro",
                duration_range=(10.0, 20.0),
                visual_style="tech_overview",
                caption_style="bold_centered",
                description="Topic introduction with tech-styled graphics",
            ),
            TemplateSectionSpec(
                section_type="content",
                duration_range=(60.0, 120.0),
                visual_style="code_walkthrough",
                caption_style="subtitle_bottom",
                description="Main technical content with code or UI visuals",
            ),
            TemplateSectionSpec(
                section_type="content",
                duration_range=(60.0, 120.0),
                visual_style="demo_screen_capture",
                caption_style="subtitle_bottom",
                description="Demo or screen recording section",
            ),
            TemplateSectionSpec(
                section_type="content",
                duration_range=(30.0, 60.0),
                visual_style="comparison_grid",
                caption_style="subtitle_bottom",
                description="Comparison or benchmark results",
            ),
            TemplateSectionSpec(
                section_type="cta",
                duration_range=(10.0, 20.0),
                visual_style="neon_subscribe",
                caption_style="bold_centered",
                description="Tech-styled CTA with neon accents",
            ),
        ],
        transition_style="slide_left",
        music_genre="electronic_synthwave",
        caption_preset="bold_centered",
        color_scheme={
            "primary": "#00FFFF",
            "secondary": "#0D0D1A",
            "accent": "#FF00FF",
            "background": "#0A0A1A",
            "text": "#FFFFFF",
            "code_bg": "#1E1E3F",
            "neon_glow": "#00FFFF",
        },
        pacing="medium",
        target_duration_range=(480.0, 900.0),
        tags=["tech", "programming", "ai", "futuristic", "modern"],
    ),
}


# ── Lookup helper ────────────────────────────────────────────────────────────

def get_template(name: str) -> VideoTemplate:
    """Retrieve a built-in template by name.

    Parameters:
        name: Template name (case-insensitive, underscores / hyphens / spaces
            are normalised).

    Returns:
        The matching :class:`VideoTemplate`.

    Raises:
        ValueError: If *name* does not match any built-in template.
    """
    key = name.lower().strip().replace("-", "_").replace(" ", "_")
    if key not in BUILT_IN_TEMPLATES:
        valid = ", ".join(sorted(BUILT_IN_TEMPLATES))
        raise ValueError(f"Unknown template '{name}'. Available: {valid}")
    return BUILT_IN_TEMPLATES[key]


def list_templates() -> list[dict[str, str]]:
    """Return a summary list of all built-in templates.

    Returns:
        List of dicts with ``name``, ``description``, ``format``, and ``pacing``.
    """
    return [
        {
            "name": t.name,
            "description": t.description,
            "format": t.format.value,
            "pacing": t.pacing,
        }
        for t in BUILT_IN_TEMPLATES.values()
    ]
