"""DALL-E 3 image generator implementation."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import openai

from aividio.services.imagegen.base import ImageGenerator
from aividio.utils.retry import retry

if TYPE_CHECKING:
    from aividio.config.settings import Settings

# DALL-E 3 supported sizes
_DALLE_SIZES = {
    "1024x1024": "1024x1024",
    "1792x1024": "1792x1024",  # landscape
    "1024x1792": "1024x1792",  # portrait
    # Map common video sizes to closest DALL-E size
    "1280x720": "1792x1024",
    "1920x1080": "1792x1024",
    "720x1280": "1024x1792",
    "1080x1920": "1024x1792",
}


class DalleImageGenerator(ImageGenerator):
    """Generate images via OpenAI DALL-E 3."""

    MODEL = "dall-e-3"

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__(settings=settings)
        api_key = self.settings.openai_api_key.get_secret_value()
        if not api_key:
            raise ValueError(
                "openai_api_key is not configured. "
                "Set AIVIDIO_OPENAI_API_KEY in your environment."
            )
        self._client = openai.OpenAI(api_key=api_key)

    def _resolve_size(self, size: str) -> str:
        """Map a requested size to one DALL-E 3 supports."""
        if size in _DALLE_SIZES:
            return _DALLE_SIZES[size]
        self.logger.warning(
            "Unsupported DALL-E size %r, defaulting to 1792x1024", size
        )
        return "1792x1024"

    @retry(max_attempts=3, base_delay=3.0, exceptions=(openai.APIError,))
    def generate(
        self,
        prompt: str,
        size: str = "1280x720",
        output_path: Path | None = None,
    ) -> Path:
        """Generate an image with DALL-E 3 and save to disk."""
        dalle_size = self._resolve_size(size)
        self.logger.info(
            "DALL-E 3 generate: prompt=%r, size=%s->%s",
            prompt[:80],
            size,
            dalle_size,
        )

        response = self._client.images.generate(
            model=self.MODEL,
            prompt=prompt,
            n=1,
            size=dalle_size,
            quality="hd",
            response_format="url",
        )

        image_url = response.data[0].url
        if not image_url:
            raise RuntimeError("DALL-E returned empty image URL")

        # Determine output path.
        if output_path is None:
            output_dir = Path(tempfile.gettempdir()) / "aividio" / "imagegen"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"dalle_{uuid.uuid4().hex[:12]}.png"
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)

        # Download the image.
        with httpx.stream("GET", image_url, timeout=60.0, follow_redirects=True) as resp:
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)

        self.logger.info("DALL-E 3 image saved: %s", output_path)
        return output_path
