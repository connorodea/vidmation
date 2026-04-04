"""Abstract base class for stock media providers."""

from __future__ import annotations

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
