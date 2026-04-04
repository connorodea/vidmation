"""AI image generation service — create visuals via DALL-E, Replicate, or fal."""

from __future__ import annotations

from typing import TYPE_CHECKING

from vidmation.config.settings import get_settings
from vidmation.services.imagegen.base import ImageGenerator

if TYPE_CHECKING:
    from vidmation.config.settings import Settings

__all__ = ["ImageGenerator", "create_image_generator"]


def create_image_generator(
    provider: str | None = None,
    settings: Settings | None = None,
) -> ImageGenerator:
    """Factory: return an ImageGenerator for the requested provider.

    Args:
        provider: ``"dalle"``, ``"replicate"``, or ``"fal"``.
            Falls back to ``settings.default_image_provider`` when *None*.
        settings: Optional settings override.
    """
    settings = settings or get_settings()
    provider = provider or settings.default_image_provider

    if provider == "dalle":
        from vidmation.services.imagegen.dalle import DalleImageGenerator

        return DalleImageGenerator(settings=settings)

    if provider == "replicate":
        from vidmation.services.imagegen.replicate_gen import ReplicateImageGenerator

        return ReplicateImageGenerator(settings=settings)

    if provider == "fal":
        from vidmation.services.imagegen.fal_gen import FalImageGenerator

        return FalImageGenerator(settings=settings)

    raise ValueError(f"Unknown image generation provider: {provider!r}")
