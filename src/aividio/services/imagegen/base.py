"""Abstract base class for AI image generators."""

from __future__ import annotations

from abc import abstractmethod
from pathlib import Path

from aividio.services.base import BaseService


class ImageGenerator(BaseService):
    """ABC for AI image generation services."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        size: str = "1280x720",
        output_path: Path | None = None,
    ) -> Path:
        """Generate an image from *prompt*.

        Args:
            prompt: Text description of the desired image.
            size: Dimensions as ``"WIDTHxHEIGHT"`` (e.g. ``"1280x720"``).
            output_path: Where to save the image.  If *None*, a temp path
                is chosen automatically.

        Returns:
            Path to the saved image file.
        """
        ...
