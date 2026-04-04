"""fal.ai image generator implementation (Flux models)."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import fal_client

from vidmation.services.imagegen.base import ImageGenerator
from vidmation.utils.retry import retry

if TYPE_CHECKING:
    from vidmation.config.settings import Settings

# Default fal model endpoint — Flux Pro.
DEFAULT_MODEL = "fal-ai/flux/dev"


class FalImageGenerator(ImageGenerator):
    """Generate images via fal.ai (Flux models)."""

    def __init__(
        self,
        settings: Settings | None = None,
        model_id: str = DEFAULT_MODEL,
    ) -> None:
        super().__init__(settings=settings)
        fal_key = self.settings.fal_key.get_secret_value()
        if not fal_key:
            raise ValueError(
                "fal_key is not configured. "
                "Set VIDMATION_FAL_KEY in your environment."
            )
        # fal_client reads FAL_KEY from the environment; set it explicitly.
        import os

        os.environ["FAL_KEY"] = fal_key
        self._model_id = model_id

    def _parse_size(self, size: str) -> tuple[int, int]:
        """Parse ``'WIDTHxHEIGHT'`` into ``(width, height)``."""
        try:
            w, h = size.lower().split("x")
            return int(w), int(h)
        except (ValueError, AttributeError):
            self.logger.warning("Invalid size %r, defaulting to 1280x720", size)
            return 1280, 720

    @retry(max_attempts=3, base_delay=5.0, exceptions=(Exception,))
    def generate(
        self,
        prompt: str,
        size: str = "1280x720",
        output_path: Path | None = None,
    ) -> Path:
        """Generate an image via fal.ai and save to disk."""
        width, height = self._parse_size(size)
        self.logger.info(
            "fal.ai generate: model=%s, prompt=%r, size=%dx%d",
            self._model_id,
            prompt[:80],
            width,
            height,
        )

        result: dict[str, Any] = fal_client.subscribe(
            self._model_id,
            arguments={
                "prompt": prompt,
                "image_size": {
                    "width": width,
                    "height": height,
                },
                "num_images": 1,
            },
        )

        # Extract image URL from result.
        images = result.get("images", [])
        if not images:
            raise RuntimeError("fal.ai returned no images")
        image_url = images[0].get("url", "")
        if not image_url:
            raise RuntimeError("fal.ai returned an image entry with no URL")

        # Determine output path.
        if output_path is None:
            output_dir = Path(tempfile.gettempdir()) / "vidmation" / "imagegen"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"fal_{uuid.uuid4().hex[:12]}.png"
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)

        # Download the generated image.
        with httpx.stream("GET", image_url, timeout=120.0, follow_redirects=True) as resp:
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)

        self.logger.info("fal.ai image saved: %s", output_path)
        return output_path
