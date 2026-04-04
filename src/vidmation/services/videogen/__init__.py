"""AI video generation service — create clips via Replicate, fal.ai, or local FFmpeg."""

from __future__ import annotations

from typing import TYPE_CHECKING

from vidmation.config.settings import get_settings
from vidmation.services.videogen.base import VideoGenerator

if TYPE_CHECKING:
    from vidmation.config.settings import Settings

__all__ = ["VideoGenerator", "create_video_generator"]


def create_video_generator(
    provider: str | None = None,
    model_id: str | None = None,
    settings: Settings | None = None,
) -> VideoGenerator:
    """Factory: return a VideoGenerator for the requested provider.

    Args:
        provider: ``"replicate"``, ``"fal"``, or ``"local"``.
            Falls back to ``settings.default_video_provider`` if that exists,
            otherwise ``"replicate"``.
        model_id: Optional model identifier to pass to the generator.
        settings: Optional settings override.
    """
    settings = settings or get_settings()

    # Determine provider — use a sensible default
    if provider is None:
        provider = getattr(settings, "default_video_provider", "replicate")

    if provider == "replicate":
        from vidmation.services.videogen.replicate_vid import ReplicateVideoGenerator

        kwargs: dict = {"settings": settings}
        if model_id:
            kwargs["model_id"] = model_id
        return ReplicateVideoGenerator(**kwargs)

    if provider == "fal":
        from vidmation.services.videogen.fal_vid import FalVideoGenerator

        kwargs = {"settings": settings}
        if model_id:
            kwargs["model_id"] = model_id
        return FalVideoGenerator(**kwargs)

    if provider == "local":
        from vidmation.services.videogen.local_gen import LocalVideoGenerator

        return LocalVideoGenerator(settings=settings)

    raise ValueError(f"Unknown video generation provider: {provider!r}")
