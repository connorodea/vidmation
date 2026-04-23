"""Dynamic caption animations for AIVIDIO.

Submagic-style animated captions with 35+ templates inspired by popular
creators and visual styles.  Generates Advanced SubStation Alpha (.ass)
subtitle files with rich override-tag animations that can be burned into
video via ffmpeg's ``ass`` filter.

Submodules
----------
- **templates** -- Caption template dataclass and the full template registry.
- **animator**  -- :class:`CaptionAnimator` turns word timestamps + a template
  into a fully animated ASS file.
- **effects**   -- Low-level ASS override-tag helpers (bounce, pop, fade,
  glow, highlight, etc.).
"""

from __future__ import annotations

from aividio.captions.animator import CaptionAnimator
from aividio.captions.effects import (
    bg_highlight,
    bounce_in,
    color_highlight,
    fade_in,
    glow,
    pop_in,
    shake,
    slide_up,
)
from aividio.captions.templates import (
    TEMPLATES,
    CaptionTemplate,
    create_custom_template,
    get_template,
    list_templates,
)

__all__ = [
    # animator
    "CaptionAnimator",
    # templates
    "CaptionTemplate",
    "TEMPLATES",
    "create_custom_template",
    "get_template",
    "list_templates",
    # effects
    "bg_highlight",
    "bounce_in",
    "color_highlight",
    "fade_in",
    "glow",
    "pop_in",
    "shake",
    "slide_up",
]
