"""YouTube video uploader with resumable upload support."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httplib2
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from vidmation.utils.retry import retry

if TYPE_CHECKING:
    from google.oauth2.credentials import Credentials

logger = logging.getLogger("vidmation.services.youtube.uploader")

# Maximum number of resumable upload retries.
_MAX_RESUMABLE_RETRIES = 10
# Chunk size for resumable upload (10 MB).
_CHUNK_SIZE = 10 * 1024 * 1024

# Retry-able HTTP status codes.
_RETRYABLE_STATUS_CODES = {500, 502, 503, 504}


class YouTubeUploader:
    """Upload videos to YouTube via the Data API v3.

    Uses resumable uploads so large files can survive transient network
    failures.
    """

    def __init__(self, credentials: "Credentials") -> None:
        self._service = build(
            "youtube",
            "v3",
            credentials=credentials,
            cache_discovery=False,
        )

    def upload(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str] | None = None,
        category_id: str = "22",
        thumbnail_path: Path | None = None,
        visibility: str = "private",
    ) -> str:
        """Upload a video to YouTube.

        Args:
            video_path: Path to the video file.
            title: Video title (max 100 chars).
            description: Video description (max 5000 chars).
            tags: List of tags.
            category_id: YouTube category ID (``"22"`` = People & Blogs).
            thumbnail_path: Optional custom thumbnail image to set.
            visibility: ``"public"``, ``"unlisted"``, or ``"private"``.

        Returns:
            The YouTube video ID of the uploaded video.
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        logger.info(
            "Uploading video: title=%r, path=%s, visibility=%s",
            title,
            video_path,
            visibility,
        )

        body: dict[str, Any] = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags or [],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": visibility,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            str(video_path),
            chunksize=_CHUNK_SIZE,
            resumable=True,
            mimetype="video/*",
        )

        request = self._service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        video_id = self._execute_resumable_upload(request)

        # Set custom thumbnail if provided.
        if thumbnail_path and thumbnail_path.exists():
            self._set_thumbnail(video_id, thumbnail_path)

        logger.info("Upload complete: video_id=%s", video_id)
        return video_id

    def _execute_resumable_upload(self, request: Any) -> str:
        """Execute a resumable upload with retry logic.

        Returns the video ID.
        """
        response = None
        retry_count = 0

        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.info("Upload progress: %d%%", progress)
            except HttpError as exc:
                if exc.resp.status in _RETRYABLE_STATUS_CODES:
                    retry_count += 1
                    if retry_count > _MAX_RESUMABLE_RETRIES:
                        logger.error(
                            "Upload failed after %d retries", _MAX_RESUMABLE_RETRIES
                        )
                        raise
                    wait = min(2 ** retry_count, 60)
                    logger.warning(
                        "Retryable error %d, retry %d/%d in %ds",
                        exc.resp.status,
                        retry_count,
                        _MAX_RESUMABLE_RETRIES,
                        wait,
                    )
                    time.sleep(wait)
                else:
                    raise
            except httplib2.HttpLib2Error as exc:
                retry_count += 1
                if retry_count > _MAX_RESUMABLE_RETRIES:
                    raise
                wait = min(2 ** retry_count, 60)
                logger.warning(
                    "Transport error, retry %d/%d in %ds: %s",
                    retry_count,
                    _MAX_RESUMABLE_RETRIES,
                    wait,
                    exc,
                )
                time.sleep(wait)

        video_id: str = response["id"]
        return video_id

    @retry(max_attempts=3, base_delay=2.0, exceptions=(HttpError,))
    def _set_thumbnail(self, video_id: str, thumbnail_path: Path) -> None:
        """Set a custom thumbnail on an uploaded video."""
        logger.info("Setting thumbnail for %s: %s", video_id, thumbnail_path)

        media = MediaFileUpload(
            str(thumbnail_path),
            mimetype="image/jpeg",
        )

        self._service.thumbnails().set(
            videoId=video_id,
            media_body=media,
        ).execute()

        logger.info("Thumbnail set successfully for %s", video_id)
