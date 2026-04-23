"""Video style presets and templates for different channel types.

Public API::

    from aividio.styles import (
        # Low-level image/grade presets
        VideoStyle, get_style, list_styles, build_image_prompt, get_ffmpeg_grade,
        # High-level video templates (caption + transition + music + thumbnail)
        VideoTemplate, VIDEO_TEMPLATES,
    )
    from aividio.styles.registry import get_template, list_templates, apply_template
"""
