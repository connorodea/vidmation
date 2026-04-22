"""Pexels stock media provider implementation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

from aividio.services.media.base import MediaProvider
from aividio.utils.retry import retry

if TYPE_CHECKING:
    from aividio.config.settings import Settings

_BASE_URL = "https://api.pexels.com"


class PexelsMediaProvider(MediaProvider):
    """Search and download stock videos / images from Pexels."""

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__(settings=settings)
        api_key = self.settings.pexels_api_key.get_secret_value()
        if not api_key:
            raise ValueError(
                "pexels_api_key is not configured. "
                "Set VIDMATION_PEXELS_API_KEY in your environment."
            )
        self._api_key = api_key
        self._http = httpx.Client(
            base_url=_BASE_URL,
            headers={"Authorization": self._api_key},
            timeout=30.0,
        )

    # ------------------------------------------------------------------
    # Videos
    # ------------------------------------------------------------------

    @retry(max_attempts=3, base_delay=1.5, exceptions=(httpx.HTTPError,))
    def search_videos(self, query: str, count: int = 5) -> list[dict]:
        """Search Pexels for stock videos."""
        self.logger.info("Pexels video search: query=%r, count=%d", query, count)

        resp = self._http.get(
            "/videos/search",
            params={"query": query, "per_page": count, "orientation": "landscape"},
        )
        resp.raise_for_status()
        data = resp.json()

        results: list[dict] = []
        for item in data.get("videos", []):
            # Pick the best HD video file.
            video_file = self._pick_video_file(item.get("video_files", []))
            if not video_file:
                continue
            results.append(
                {
                    "id": str(item["id"]),
                    "url": item.get("url", ""),
                    "download_url": video_file["link"],
                    "width": video_file.get("width", 0),
                    "height": video_file.get("height", 0),
                    "duration": item.get("duration", 0),
                    "source": "pexels",
                    "attribution": f"Video by {item.get('user', {}).get('name', 'Unknown')} on Pexels",
                }
            )

        self.logger.info("Pexels video search returned %d results", len(results))
        return results

    @staticmethod
    def _pick_video_file(files: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Select the best quality video file (prefer HD, then largest)."""
        if not files:
            return None
        # Prefer files labelled 'hd' or with width >= 1280
        hd_files = [f for f in files if f.get("quality") == "hd" or f.get("width", 0) >= 1280]
        if hd_files:
            return max(hd_files, key=lambda f: f.get("width", 0))
        return max(files, key=lambda f: f.get("width", 0))

    # ------------------------------------------------------------------
    # Images
    # ------------------------------------------------------------------

    @retry(max_attempts=3, base_delay=1.5, exceptions=(httpx.HTTPError,))
    def search_images(self, query: str, count: int = 5) -> list[dict]:
        """Search Pexels for stock photos."""
        self.logger.info("Pexels image search: query=%r, count=%d", query, count)

        resp = self._http.get(
            "/v1/search",
            params={"query": query, "per_page": count, "orientation": "landscape"},
        )
        resp.raise_for_status()
        data = resp.json()

        results: list[dict] = []
        for item in data.get("photos", []):
            src = item.get("src", {})
            results.append(
                {
                    "id": str(item["id"]),
                    "url": item.get("url", ""),
                    "download_url": src.get("large2x") or src.get("original", ""),
                    "width": item.get("width", 0),
                    "height": item.get("height", 0),
                    "source": "pexels",
                    "attribution": f"Photo by {item.get('photographer', 'Unknown')} on Pexels",
                }
            )

        self.logger.info("Pexels image search returned %d results", len(results))
        return results

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    @retry(max_attempts=3, base_delay=2.0, exceptions=(httpx.HTTPError,))
    def download(self, url: str, output_path: Path) -> Path:
        """Download a media file from Pexels to *output_path*."""
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
