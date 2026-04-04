"""Abstract base class for AI video generators."""

from __future__ import annotations

from abc import abstractmethod
from pathlib import Path

from vidmation.services.base import BaseService


class VideoGenerator(BaseService):
    """ABC for AI video generation services.

    Implementations wrap external APIs (Replicate, fal.ai) or local FFmpeg
    pipelines to produce short video clips from text prompts or reference
    images.
    """

    @abstractmethod
    def generate(
        self,
        prompt: str,
        duration: float = 5.0,
        aspect_ratio: str = "16:9",
        output_path: Path | None = None,
    ) -> Path:
        """Generate a video clip from a text prompt.

        Args:
            prompt: Text description of the desired video.
            duration: Target clip length in seconds.
            aspect_ratio: Aspect ratio string (e.g. ``"16:9"``, ``"9:16"``).
            output_path: Where to save the video.  If *None*, a temp path
                is chosen automatically.

        Returns:
            Path to the saved video file.
        """
        ...

    @abstractmethod
    def generate_from_image(
        self,
        image_path: Path,
        prompt: str,
        duration: float = 5.0,
        output_path: Path | None = None,
    ) -> Path:
        """Generate a video clip from a reference image (image-to-video).

        Args:
            image_path: Path to the source image.
            prompt: Motion / style description to guide animation.
            duration: Target clip length in seconds.
            output_path: Where to save the video.  If *None*, a temp path
                is chosen automatically.

        Returns:
            Path to the saved video file.
        """
        ...

    @abstractmethod
    def list_models(self) -> list[dict]:
        """Return metadata for all models supported by this generator.

        Each dict contains at minimum:
        ``{"id": str, "name": str, "supports_i2v": bool, "max_duration": float}``
        """
        ...

    @abstractmethod
    def estimate_cost(self, duration: float, model: str | None = None) -> float:
        """Estimate the USD cost for generating a clip of the given duration.

        Args:
            duration: Target clip length in seconds.
            model: Optional model identifier.  Uses the generator's default
                model when *None*.

        Returns:
            Estimated cost in USD.
        """
        ...
