"""Brand kit and template system for VIDMATION.

Submodules:
- kit: :class:`BrandKit` dataclass for logos, colors, fonts, intros/outros.
- templates: :class:`VideoTemplate` system with built-in presets.
- overlays: FFmpeg-based overlay engine for logos, watermarks, lower thirds.
"""

from vidmation.brand.kit import BrandKit, BrandKitColors, BrandKitFonts, LowerThirdStyle
from vidmation.brand.overlays import (
    add_logo_overlay,
    add_lower_third,
    add_text_overlay,
    add_watermark,
)
from vidmation.brand.templates import (
    BUILT_IN_TEMPLATES,
    TemplateSectionSpec,
    VideoTemplate,
    get_template,
)

__all__ = [
    # kit
    "BrandKit",
    "BrandKitColors",
    "BrandKitFonts",
    "LowerThirdStyle",
    # overlays
    "add_logo_overlay",
    "add_lower_third",
    "add_text_overlay",
    "add_watermark",
    # templates
    "BUILT_IN_TEMPLATES",
    "TemplateSectionSpec",
    "VideoTemplate",
    "get_template",
]
