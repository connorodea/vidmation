"""Post-production effects — auto-zoom, silence removal, B-roll, emoji/SFX, and magic clips."""

from aividio.effects.emoji_sfx import EmojiSFXEngine
from aividio.effects.magic_broll import MagicBRoll
from aividio.effects.magic_clips import MagicClips
from aividio.effects.magic_zoom import MagicZoom
from aividio.effects.silence_remover import SilenceRemover

__all__ = [
    "EmojiSFXEngine",
    "MagicBRoll",
    "MagicClips",
    "MagicZoom",
    "SilenceRemover",
]
