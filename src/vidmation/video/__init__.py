"""Video assembly engine for VIDMATION.

Submodules:
- assembler: Main :class:`VideoAssembler` orchestration class.
- audio_mixer: Voiceover + music mixing utilities.
- captions_render: ASS subtitle generation and burn-in.
- transitions: FFmpeg filter-graph transition effects.
- formats: Video format specifications (landscape, portrait, short).
"""

from vidmation.video.assembler import VideoAssembler
from vidmation.video.audio_mixer import (
    get_audio_duration,
    mix_voiceover_and_music,
    normalize_audio,
)
from vidmation.video.captions_render import burn_captions, generate_ass_file
from vidmation.video.formats import (
    FORMAT_REGISTRY,
    LANDSCAPE,
    PORTRAIT,
    SHORT,
    FormatSpec,
    get_format,
)
from vidmation.video.transitions import (
    TRANSITION_REGISTRY,
    crossfade,
    crossfade_with_offset,
    cut,
    fade_black,
    get_transition,
    slide_left,
    slide_right,
)

__all__ = [
    # assembler
    "VideoAssembler",
    # audio_mixer
    "get_audio_duration",
    "mix_voiceover_and_music",
    "normalize_audio",
    # captions_render
    "burn_captions",
    "generate_ass_file",
    # formats
    "FORMAT_REGISTRY",
    "FormatSpec",
    "LANDSCAPE",
    "PORTRAIT",
    "SHORT",
    "get_format",
    # transitions
    "TRANSITION_REGISTRY",
    "crossfade",
    "crossfade_with_offset",
    "cut",
    "fade_black",
    "get_transition",
    "slide_left",
    "slide_right",
]
