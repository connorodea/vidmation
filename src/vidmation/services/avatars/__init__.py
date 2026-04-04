"""AI avatar generation — talking-head video synthesis from text and images."""

from __future__ import annotations

from typing import TYPE_CHECKING

from vidmation.config.settings import get_settings
from vidmation.services.avatars.base import AvatarProvider

if TYPE_CHECKING:
    from vidmation.config.settings import Settings

__all__ = ["AvatarProvider", "create_avatar_provider"]


def create_avatar_provider(
    provider: str = "replicate",
    settings: Settings | None = None,
) -> AvatarProvider:
    """Factory: return an AvatarProvider for the requested backend.

    Args:
        provider: ``"replicate"`` or ``"fal"``.
        settings: Optional settings override.
    """
    settings = settings or get_settings()

    if provider == "replicate":
        from vidmation.services.avatars.replicate_avatar import ReplicateAvatarProvider

        return ReplicateAvatarProvider(settings=settings)

    if provider == "fal":
        from vidmation.services.avatars.fal_avatar import FalAvatarProvider

        return FalAvatarProvider(settings=settings)

    raise ValueError(f"Unknown avatar provider: {provider!r}")
