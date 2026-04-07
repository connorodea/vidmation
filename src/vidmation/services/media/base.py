"""Abstract base class for stock media providers."""

from __future__ import annotations

import uuid
from abc import abstractmethod
from pathlib import Path

from vidmation.services.base import BaseService


class MediaProvider(BaseService):
    """ABC for stock video / image search and download services."""

    @abstractmethod
    def search_videos(self, query: str, count: int = 5) -> list[dict]:
        """Search for stock videos matching *query*.

        Returns a list of dicts, each with at minimum::

            {
                "id": str,
                "url": str,           # page URL
                "download_url": str,   # direct download link
                "width": int,
                "height": int,
                "duration": float,     # seconds
                "source": str,         # provider name
                "attribution": str,
            }
        """
        ...

    @abstractmethod
    def search_images(self, query: str, count: int = 5) -> list[dict]:
        """Search for stock images matching *query*.

        Returns a list of dicts, each with at minimum::

            {
                "id": str,
                "url": str,
                "download_url": str,
                "width": int,
                "height": int,
                "source": str,
                "attribution": str,
            }
        """
        ...

    @abstractmethod
    def download(self, url: str, output_path: Path) -> Path:
        """Download a media file from *url* to *output_path*.

        Returns the resolved output path.
        """
        ...

    def search_and_download(
        self,
        query: str,
        media_type: str,
        output_dir: Path,
        section_index: int,
        count: int = 5,
    ) -> dict:
        """Search for media and download the best result.

        Convenience method used by the pipeline's ``stage_media_sourcing``
        stage.  It delegates to ``search_videos`` or ``search_images``,
        picks the first result, downloads it, and returns a result dict::

            {
                "path": Path,
                "source": str,
                "attribution": str,
            }

        Args:
            query: Search query string.
            media_type: ``"video"`` or ``"image"`` (anything else falls back
                to video).
            output_dir: Directory to download the file into.
            section_index: Used to name the output file deterministically.
            count: Number of results to fetch from the provider.

        Raises:
            RuntimeError: If no results are found for the query.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        if media_type in ("image", "stock_image", "ai_image"):
            results = self.search_images(query=query, count=count)
            ext = ".jpg"
        else:
            results = self.search_videos(query=query, count=count)
            ext = ".mp4"

        if not results:
            raise RuntimeError(
                f"No {media_type} results found for query={query!r}"
            )

        best = results[0]
        filename = f"section_{section_index}_{uuid.uuid4().hex[:8]}{ext}"
        output_path = output_dir / filename

        self.download(url=best["download_url"], output_path=output_path)

        return {
            "path": output_path,
            "source": best.get("source", "unknown"),
            "attribution": best.get("attribution", ""),
        }
