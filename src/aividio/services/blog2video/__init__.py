"""Blog-to-video service — scrape a blog URL and generate a video script."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aividio.services.blog2video.converter import BlogToVideoConverter
from aividio.services.blog2video.scraper import BlogScraper

if TYPE_CHECKING:
    from aividio.config.settings import Settings

__all__ = ["BlogScraper", "BlogToVideoConverter", "create_blog_converter"]


def create_blog_converter(settings: Settings | None = None) -> BlogToVideoConverter:
    """Factory: return a BlogToVideoConverter."""
    from aividio.config.settings import get_settings

    settings = settings or get_settings()
    return BlogToVideoConverter(settings=settings)
