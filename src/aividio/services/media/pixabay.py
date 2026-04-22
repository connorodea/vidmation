"""Pixabay stock media provider implementation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import httpx

from aividio.services.media.base import MediaProvider
from aividio.utils.retry import retry

if TYPE_CHECKING:
    from aividio.config.settings import Settings

_BASE_URL = "https://pixabay.com/api"


class PixabayMediaProvider(MediaProvider):
    """Search and download stock videos / images from Pixabay."""

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__(settings=settings)
        api_key = self.settings.pixabay_api_key.get_secret_value()
        if not api_key:
            raise ValueError(
                "pixabay_api_key is not configured. "
                "Set VIDMATION_PIXABAY_API_KEY in your environment."
            )
        self._api_key = api_key
        self._http = httpx.Client(
            base_url=_BASE_URL,
            timeout=30.0,
        )

    # ------------------------------------------------------------------
    # Videos
    # ------------------------------------------------------------------

    @retry(max_attempts=3, base_delay=1.5, exceptions=(httpx.HTTPError,))
    def search_videos(self, query: str, count: int = 5) -> list[dict]:
        """Search Pixabay for stock videos."""
        self.logger.info("Pixabay video search: query=%r, count=%d", query, count)

        resp = self._http.get(
            "/videos/",
            params={
                "key": self._api_key,
                "q": query,
                "per_page": count,
                "orientation": "horizontal",
                "safesearch": "true",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        results: list[dict] = []
        for item in data.get("hits", []):
            videos = item.get("videos", {})
            # Prefer "large" then "medium" quality.
            video_data = videos.get("large") or videos.get("medium") or {}
            download_url = video_data.get("url", "")
            if not download_url:
                continue

            results.append(
                {
                    "id": str(item.get("id", "")),
                    "url": item.get("pageURL", ""),
                    "download_url": download_url,
                    "width": video_data.get("width", 0),
                    "height": video_data.get("height", 0),
                    "duration": item.get("duration", 0),
                    "source": "pixabay",
                    "attribution": f"Video by {item.get('user', 'Unknown')} on Pixabay",
                }
            )

        self.logger.info("Pixabay video search returned %d results", len(results))
        return results

    # ------------------------------------------------------------------
    # Images
    # ------------------------------------------------------------------

    @retry(max_attempts=3, base_delay=1.5, exceptions=(httpx.HTTPError,))
    def search_images(self, query: str, count: int = 5) -> list[dict]:
        """Search Pixabay for stock photos."""
        self.logger.info("Pixabay image search: query=%r, count=%d", query, count)

        resp = self._http.get(
            "/",
            params={
                "key": self._api_key,
                "q": query,
                "per_page": count,
                "orientation": "horizontal",
                "image_type": "photo",
                "safesearch": "true",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        results: list[dict] = []
        for item in data.get("hits", []):
            results.append(
                {
                    "id": str(item.get("id", "")),
                    "url": item.get("pageURL", ""),
                    "download_url": item.get("largeImageURL", ""),
                    "width": item.get("imageWidth", 0),
                    "height": item.get("imageHeight", 0),
                    "source": "pixabay",
                    "attribution": f"Image by {item.get('user', 'Unknown')} on Pixabay",
                }
            )

        self.logger.info("Pixabay image search returned %d results", len(results))
        return results

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    @retry(max_attempts=3, base_delay=2.0, exceptions=(httpx.HTTPError,))
    def download(self, url: str, output_path: Path) -> Path:
        """Download a media file from Pixabay to *output_path*."""
        self.logger.info("Downloading %s -> %s", url, output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with httpx.stream("GET", url, timeout=60.0, follow_redirects=True) as resp:
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)

        self.logger.info(
            "Download complete: %s (%.1f MB)",
            output_path.name,
            output_path.stat().st_size / 1_048_576,
        )
        return output_path
