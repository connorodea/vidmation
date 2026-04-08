"""Blog-to-video service — scrape a blog URL and generate a video script."""

from __future__ import annotations

from typing import TYPE_CHECKING

from vidmation.services.blog2video.converter import BlogToVideoConverter
from vidmation.services.blog2video.scraper import BlogScraper

if TYPE_CHECKING:
    from vidmation.config.settings import Settings

__all__ = ["BlogScraper", "BlogToVideoConverter", "create_blog_converter"]


def create_blog_converter(settings: Settings | None = None) -> BlogToVideoConverter:
    """Factory: return a BlogToVideoConverter."""
    from vidmation.config.settings import get_settings

    settings = settings or get_settings()
    return BlogToVideoConverter(settings=settings)
