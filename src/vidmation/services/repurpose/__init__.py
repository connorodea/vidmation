"""Content repurposing service — turn YouTube scripts into social media content."""

from __future__ import annotations

from typing import TYPE_CHECKING

from vidmation.config.settings import get_settings

if TYPE_CHECKING:
    from vidmation.config.settings import Settings
    from vidmation.services.repurpose.generator import ContentRepurposer as ContentRepurposer

__all__ = ["ContentRepurposer", "create_repurposer"]


def create_repurposer(
    settings: Settings | None = None,
) -> "ContentRepurposer":
    """Factory: return a ContentRepurposer instance.

    Args:
        settings: Optional settings override.  Falls back to the global
            ``Settings`` singleton when *None*.
    """
    from vidmation.services.repurpose.generator import ContentRepurposer

    settings = settings or get_settings()
    return ContentRepurposer(settings=settings)
