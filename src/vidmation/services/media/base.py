"""Abstract base class for stock media providers."""

from __future__ import annotations

import logging
import uuid
from abc import abstractmethod
from pathlib import Path

from vidmation.services.base import BaseService

logger = logging.getLogger(__name__)


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

    def search_and_download_multiple(
        self,
        queries: list[str],
        media_type: str,
        output_dir: Path,
        section_index: int,
        clips_per_section: int = 4,
    ) -> list[dict]:
        """Search using multiple queries and download several clips per section.

        This produces the variety needed for faceless YouTube videos where
        visuals should change every 3-5 seconds.  Multiple search queries
        (variations of the visual concept) are used to avoid downloading
        near-duplicate clips.

        Args:
            queries: A list of 1-3 search query variations for this section.
            media_type: ``"video"`` or ``"image"`` (anything else falls back
                to video).
            output_dir: Directory to download files into.
            section_index: Used to name output files deterministically.
            clips_per_section: Target number of clips to download (default 4).
                Will gracefully return fewer if not enough results found.

        Returns:
            A list of result dicts, each with::

                {
                    "path": Path,
                    "source": str,
                    "attribution": str,
                }

            The list will contain between 1 and *clips_per_section* entries.

        Raises:
            RuntimeError: If zero results are found across all queries.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        is_image = media_type in ("image", "stock_image", "ai_image")
        ext = ".jpg" if is_image else ".mp4"

        # Collect results from all queries, deduplicating by download URL
        all_results: list[dict] = []
        seen_urls: set[str] = set()

        per_query_count = max(3, clips_per_section)

        for query in queries:
            try:
                if is_image:
                    results = self.search_images(query=query, count=per_query_count)
                else:
                    results = self.search_videos(query=query, count=per_query_count)
            except Exception as exc:
                logger.warning(
                    "Multi-clip search failed for query=%r: %s", query, exc
                )
                continue

            for r in results:
                url = r.get("download_url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(r)

        if not all_results:
            raise RuntimeError(
                f"No {media_type} results found across queries: {queries!r}"
            )

        # Take up to clips_per_section unique results
        to_download = all_results[:clips_per_section]

        downloaded: list[dict] = []
        for i, result in enumerate(to_download):
            filename = f"section_{section_index}_clip{i}_{uuid.uuid4().hex[:6]}{ext}"
            out_path = output_dir / filename

            try:
                self.download(url=result["download_url"], output_path=out_path)
                downloaded.append({
                    "path": out_path,
                    "source": result.get("source", "unknown"),
                    "attribution": result.get("attribution", ""),
                })
            except Exception as exc:
                logger.warning(
                    "Failed to download clip %d for section %d: %s",
                    i, section_index, exc,
                )

        if not downloaded:
            raise RuntimeError(
                f"All downloads failed for section {section_index}, "
                f"queries={queries!r}"
            )

        logger.info(
            "Multi-clip download: section %d got %d/%d clips",
            section_index, len(downloaded), clips_per_section,
        )
        return downloaded
