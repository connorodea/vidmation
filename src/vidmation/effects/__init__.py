"""Post-production effects — auto-zoom, silence removal, B-roll, emoji/SFX, and magic clips."""

from vidmation.effects.emoji_sfx import EmojiSFXEngine
from vidmation.effects.magic_broll import MagicBRoll
from vidmation.effects.magic_clips import MagicClips
from vidmation.effects.magic_zoom import MagicZoom
from vidmation.effects.silence_remover import SilenceRemover

__all__ = [
    "EmojiSFXEngine",
    "MagicBRoll",
    "MagicClips",
    "MagicZoom",
    "SilenceRemover",
]
