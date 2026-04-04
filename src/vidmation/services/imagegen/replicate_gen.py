"""Replicate image generator implementation (Flux / SDXL)."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import replicate
from replicate.exceptions import ReplicateError

from vidmation.services.imagegen.base import ImageGenerator
from vidmation.utils.retry import retry

if TYPE_CHECKING:
    from vidmation.config.settings import Settings

# Default model — Flux Schnell (fast) on Replicate.
DEFAULT_MODEL = "black-forest-labs/flux-schnell"


class ReplicateImageGenerator(ImageGenerator):
    """Generate images via Replicate (Flux, SDXL, etc.)."""

    def __init__(
        self,
        settings: Settings | None = None,
        model_id: str = DEFAULT_MODEL,
    ) -> None:
        super().__init__(settings=settings)
        api_token = self.settings.replicate_api_token.get_secret_value()
        if not api_token:
            raise ValueError(
                "replicate_api_token is not configured. "
                "Set VIDMATION_REPLICATE_API_TOKEN in your environment."
            )
        self._client = replicate.Client(api_token=api_token)
        self._model_id = model_id

    def _parse_size(self, size: str) -> tuple[int, int]:
        """Parse ``'WIDTHxHEIGHT'`` into ``(width, height)``."""
        try:
            w, h = size.lower().split("x")
            return int(w), int(h)
        except (ValueError, AttributeError):
            self.logger.warning("Invalid size %r, defaulting to 1280x720", size)
            return 1280, 720

    @retry(max_attempts=3, base_delay=5.0, exceptions=(ReplicateError, ConnectionError))
    def generate(
        self,
        prompt: str,
        size: str = "1280x720",
        output_path: Path | None = None,
    ) -> Path:
        """Generate an image via Replicate and save to disk."""
        width, height = self._parse_size(size)
        self.logger.info(
            "Replicate generate: model=%s, prompt=%r, size=%dx%d",
            self._model_id,
            prompt[:80],
            width,
            height,
        )

        output = self._client.run(
            self._model_id,
            input={
                "prompt": prompt,
                "width": width,
                "height": height,
                "num_outputs": 1,
            },
        )

        # Replicate returns a list of URLs (or FileOutput objects).
        if isinstance(output, list) and len(output) > 0:
            image_url = str(output[0])
        else:
            image_url = str(output)

        if not image_url:
            raise RuntimeError("Replicate returned empty output")

        # Determine output path.
        if output_path is None:
            output_dir = Path(tempfile.gettempdir()) / "vidmation" / "imagegen"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"replicate_{uuid.uuid4().hex[:12]}.png"
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)

        # Download the image.
        with httpx.stream("GET", image_url, timeout=120.0, follow_redirects=True) as resp:
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)

        self.logger.info("Replicate image saved: %s", output_path)
        return output_path
