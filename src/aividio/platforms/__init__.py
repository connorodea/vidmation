"""Multi-platform export support for VIDMATION.

Submodules:
- base: Abstract base class defining the platform interface.
- youtube: YouTube-specific formatting, metadata, and validation.
- tiktok: TikTok-specific reformatting and metadata.
- instagram: Instagram Reels, Feed, and Stories support.
- exporter: :class:`MultiPlatformExporter` that orchestrates cross-platform output.
"""

from aividio.platforms.base import Platform, PlatformType
from aividio.platforms.exporter import MultiPlatformExporter
from aividio.platforms.instagram import InstagramPlatform
from aividio.platforms.tiktok import TikTokPlatform
from aividio.platforms.youtube import YouTubePlatform

__all__ = [
    "MultiPlatformExporter",
    "Platform",
    "PlatformType",
    "InstagramPlatform",
    "TikTokPlatform",
    "YouTubePlatform",
]
