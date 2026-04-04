"""Multi-platform export support for VIDMATION.

Submodules:
- base: Abstract base class defining the platform interface.
- youtube: YouTube-specific formatting, metadata, and validation.
- tiktok: TikTok-specific reformatting and metadata.
- instagram: Instagram Reels, Feed, and Stories support.
- exporter: :class:`MultiPlatformExporter` that orchestrates cross-platform output.
"""

from vidmation.platforms.base import Platform, PlatformType
from vidmation.platforms.exporter import MultiPlatformExporter
from vidmation.platforms.instagram import InstagramPlatform
from vidmation.platforms.tiktok import TikTokPlatform
from vidmation.platforms.youtube import YouTubePlatform

__all__ = [
    "MultiPlatformExporter",
    "Platform",
    "PlatformType",
    "InstagramPlatform",
    "TikTokPlatform",
    "YouTubePlatform",
]
