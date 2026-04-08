"""Video style template registry.

Provides lookup, listing, and application of :class:`VideoTemplate` presets
to a :class:`ChannelProfile`.  This bridges the high-level template system
with the per-channel configuration used by the pipeline.

Usage::

    from vidmation.styles.registry import get_template, list_templates, apply_template

    tmpl = get_template("dark-cinematic")
    profile = apply_template(profile, "tiktok-viral")
    all_templates = list_templates()
"""

from __future__ import annotations

import copy

from vidmation.config.profiles import (
    ChannelProfile,
    MusicConfig,
    ThumbnailConfig,
    VideoConfig,
)
from vidmation.styles.presets import VIDEO_TEMPLATES, VideoTemplate

# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

def get_template(slug: str) -> VideoTemplate:
    """Retrieve a registered video template by *slug*.

    Parameters
    ----------
    slug:
        URL-safe identifier for the template (e.g. ``"dark-cinematic"``).

    Returns
    -------
    VideoTemplate
        A deep copy so callers can mutate without affecting the registry.

    Raises
    ------
    ValueError
        If *slug* is not a known template.
    """
    key = slug.lower().strip()
    if key not in VIDEO_TEMPLATES:
        valid = ", ".join(sorted(VIDEO_TEMPLATES))
        raise ValueError(
            f"Unknown video template '{slug}'. "
            f"Available templates: {valid}"
        )
    return copy.deepcopy(VIDEO_TEMPLATES[key])


def list_templates() -> list[dict]:
    """Return a summary list of all registered video templates.

    Each dict contains: ``name``, ``slug``, ``description``,
    ``transition``, ``music_genre``, ``color_accent``.
    """
    return [
        {
            "name": t.name,
            "slug": t.slug,
            "description": t.description,
            "transition": t.transition,
            "music_genre": t.music_genre,
            "color_accent": t.color_accent,
            "title_position": t.title_position,
        }
        for t in VIDEO_TEMPLATES.values()
    ]


# ---------------------------------------------------------------------------
# Template application
# ---------------------------------------------------------------------------

_ALIGNMENT_TO_STYLE = {
    1: "subtitle_bottom_left",
    2: "subtitle_bottom",
    5: "bold_centered",
    8: "subtitle_top",
}


def apply_template(
    profile: ChannelProfile,
    template_slug: str,
) -> ChannelProfile:
    """Return a new :class:`ChannelProfile` with the template's settings applied.

    The original *profile* is not mutated.  Only the fields that the template
    controls are overwritten; everything else (voice config, YouTube config,
    content config, etc.) is preserved from the original profile.

    Parameters
    ----------
    profile:
        The base channel profile to modify.
    template_slug:
        Slug of the video template to apply (e.g. ``"dark-cinematic"``).

    Returns
    -------
    ChannelProfile
        A new profile instance with template settings merged in.

    Raises
    ------
    ValueError
        If *template_slug* is not a known template.
    """
    template = get_template(template_slug)

    # Deep-copy the incoming profile so we never mutate the original
    new_profile = copy.deepcopy(profile)

    # -- Video config ------------------------------------------------------
    caption = template.caption_style
    new_profile.video = VideoConfig(
        format=new_profile.video.format,
        resolution=new_profile.video.resolution,
        target_duration_min=new_profile.video.target_duration_min,
        target_duration_max=new_profile.video.target_duration_max,
        transition=template.transition,
        caption_style=_ALIGNMENT_TO_STYLE.get(
            caption.get("alignment", 5), "bold_centered"
        ),
        caption_font=caption.get("font_name", "Montserrat-Bold"),
        caption_color=caption.get("primary_color", "#FFFFFF"),
        caption_outline_color=caption.get("outline_color", "#000000"),
        caption_font_size=caption.get("font_size", 48),
    )

    # -- Music config ------------------------------------------------------
    new_profile.music = MusicConfig(
        genre=template.music_genre,
        volume=new_profile.music.volume,
        source=new_profile.music.source,
    )

    # -- Thumbnail config --------------------------------------------------
    new_profile.thumbnail = ThumbnailConfig(
        provider=new_profile.thumbnail.provider,
        style=template.thumbnail_style,
        include_text=new_profile.thumbnail.include_text,
        text_position=template.title_position,
    )

    return new_profile
