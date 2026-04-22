"""Stock media service — search and download videos/images from stock providers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aividio.config.settings import get_settings
from aividio.services.media.base import MediaProvider

if TYPE_CHECKING:
    from aividio.config.settings import Settings

__all__ = ["MediaProvider", "create_media_provider"]


def create_media_provider(
    provider: str = "pexels",
    settings: Settings | None = None,
) -> MediaProvider:
    """Factory: return a MediaProvider for the requested stock library.

    Args:
        provider: ``"pexels"`` or ``"pixabay"``.
        settings: Optional settings override.
    """
    settings = settings or get_settings()

    if provider == "pexels":
        from aividio.services.media.pexels import PexelsMediaProvider

        return PexelsMediaProvider(settings=settings)

    if provider == "pixabay":
        from aividio.services.media.pixabay import PixabayMediaProvider

        return PixabayMediaProvider(settings=settings)

    raise ValueError(f"Unknown media provider: {provider!r}")
