"""YouTube video uploader with resumable upload support."""

from __future__ import annotations

import logging
import time
from datetime import datetime
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

    # ------------------------------------------------------------------
    # Scheduled upload
    # ------------------------------------------------------------------

    def upload_with_schedule(
        self,
        video_path: Path,
        title: str,
        description: str,
        publish_at: datetime | None = None,
        tags: list[str] | None = None,
        category_id: str = "22",
        thumbnail_path: Path | None = None,
    ) -> str:
        """Upload a video and optionally schedule it for future publication.

        Behaves like :meth:`upload` but when *publish_at* is supplied the video
        is uploaded as **private** with YouTube's ``publishAt`` field set so it
        automatically goes public at the requested time.

        Args:
            video_path: Path to the video file.
            title: Video title (max 100 chars).
            description: Video description (max 5000 chars).
            publish_at: When to publish.  Must be a future UTC datetime.
                If ``None`` the video is uploaded as private with no schedule.
            tags: List of tags.
            category_id: YouTube category ID (``"22"`` = People & Blogs).
            thumbnail_path: Optional custom thumbnail image to set.

        Returns:
            The YouTube video ID of the uploaded video.
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        logger.info(
            "Uploading scheduled video: title=%r, path=%s, publish_at=%s",
            title,
            video_path,
            publish_at,
        )

        status_body: dict[str, Any] = {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False,
        }

        if publish_at is not None:
            # YouTube requires ISO 8601 with timezone.  Assume UTC if naive.
            if publish_at.tzinfo is None:
                iso_ts = publish_at.strftime("%Y-%m-%dT%H:%M:%S.0Z")
            else:
                iso_ts = publish_at.isoformat()
            status_body["publishAt"] = iso_ts

        body: dict[str, Any] = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags or [],
                "categoryId": category_id,
            },
            "status": status_body,
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

        if thumbnail_path and thumbnail_path.exists():
            self._set_thumbnail(video_id, thumbnail_path)

        logger.info("Scheduled upload complete: video_id=%s", video_id)
        return video_id

    # ------------------------------------------------------------------
    # Caption / subtitle upload
    # ------------------------------------------------------------------

    @retry(max_attempts=3, base_delay=2.0, exceptions=(HttpError,))
    def upload_captions(
        self,
        video_id: str,
        srt_path: Path,
        language: str = "en",
        name: str = "English",
    ) -> str:
        """Upload an SRT file as captions/subtitles for a video.

        Args:
            video_id: The YouTube video ID to attach captions to.
            srt_path: Path to the ``.srt`` subtitle file.
            language: BCP-47 language code (e.g. ``"en"``, ``"es"``).
            name: Human-readable name for the caption track.

        Returns:
            The caption track ID.

        Raises:
            FileNotFoundError: If the SRT file does not exist.
            HttpError: On YouTube API errors (after retries).
        """
        if not srt_path.exists():
            raise FileNotFoundError(f"SRT file not found: {srt_path}")

        logger.info(
            "Uploading captions for video %s: lang=%s, path=%s",
            video_id,
            language,
            srt_path,
        )

        body: dict[str, Any] = {
            "snippet": {
                "videoId": video_id,
                "language": language,
                "name": name,
                "isDraft": False,
            },
        }

        media = MediaFileUpload(
            str(srt_path),
            mimetype="application/x-subrip",
            resumable=False,
        )

        response = (
            self._service.captions()
            .insert(
                part="snippet",
                body=body,
                media_body=media,
            )
            .execute()
        )

        caption_id: str = response["id"]
        logger.info("Captions uploaded: caption_id=%s", caption_id)
        return caption_id

    # ------------------------------------------------------------------
    # Metadata updates
    # ------------------------------------------------------------------

    @retry(max_attempts=3, base_delay=2.0, exceptions=(HttpError,))
    def update_video_metadata(
        self,
        video_id: str,
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Update title, description, and/or tags on an already-uploaded video.

        Only the fields that are provided (not ``None``) will be changed.  The
        method first fetches the current snippet so unchanged fields are
        preserved.

        Args:
            video_id: The YouTube video ID to update.
            title: New title (max 100 chars), or ``None`` to keep existing.
            description: New description (max 5000 chars), or ``None``.
            tags: New tag list, or ``None`` to keep existing.

        Returns:
            The updated video resource as a dict.

        Raises:
            HttpError: On YouTube API errors (after retries).
        """
        logger.info("Updating metadata for video %s", video_id)

        # Fetch current snippet so we don't blank fields the caller didn't set.
        current = (
            self._service.videos()
            .list(part="snippet", id=video_id)
            .execute()
        )

        if not current.get("items"):
            raise ValueError(f"Video not found: {video_id}")

        snippet = current["items"][0]["snippet"]

        if title is not None:
            snippet["title"] = title[:100]
        if description is not None:
            snippet["description"] = description[:5000]
        if tags is not None:
            snippet["tags"] = tags

        # categoryId is required on update even if unchanged.
        body: dict[str, Any] = {
            "id": video_id,
            "snippet": {
                "title": snippet["title"],
                "description": snippet["description"],
                "tags": snippet.get("tags", []),
                "categoryId": snippet.get("categoryId", "22"),
            },
        }

        response = (
            self._service.videos()
            .update(part="snippet", body=body)
            .execute()
        )

        logger.info("Metadata updated for video %s", video_id)
        return response

    # ------------------------------------------------------------------
    # Channel listing
    # ------------------------------------------------------------------

    @retry(max_attempts=3, base_delay=2.0, exceptions=(HttpError,))
    def list_channel_videos(
        self,
        max_results: int = 25,
        order: str = "date",
    ) -> list[dict[str, Any]]:
        """List videos on the authenticated channel.

        Args:
            max_results: Maximum number of results to return (1-50).
            order: Sort order: ``"date"``, ``"rating"``, ``"viewCount"``,
                ``"relevance"``, or ``"title"``.

        Returns:
            A list of dicts, each containing ``id``, ``title``,
            ``publishedAt``, ``viewCount``, and ``status``.

        Raises:
            HttpError: On YouTube API errors (after retries).
        """
        logger.info(
            "Listing channel videos: max_results=%d, order=%s",
            max_results,
            order,
        )

        # First, get the uploads playlist for the authenticated channel.
        channels_resp = (
            self._service.channels()
            .list(part="contentDetails", mine=True)
            .execute()
        )

        if not channels_resp.get("items"):
            logger.warning("No channel found for authenticated user")
            return []

        uploads_playlist_id = channels_resp["items"][0]["contentDetails"][
            "relatedPlaylists"
        ]["uploads"]

        # Fetch video IDs from the uploads playlist.
        playlist_resp = (
            self._service.playlistItems()
            .list(
                part="snippet",
                playlistId=uploads_playlist_id,
                maxResults=min(max_results, 50),
            )
            .execute()
        )

        items = playlist_resp.get("items", [])
        if not items:
            return []

        video_ids = [
            item["snippet"]["resourceId"]["videoId"] for item in items
        ]

        # Fetch full details (snippet + statistics + status) for the videos.
        videos_resp = (
            self._service.videos()
            .list(
                part="snippet,statistics,status",
                id=",".join(video_ids),
            )
            .execute()
        )

        results: list[dict[str, Any]] = []
        for video in videos_resp.get("items", []):
            results.append(
                {
                    "id": video["id"],
                    "title": video["snippet"]["title"],
                    "publishedAt": video["snippet"]["publishedAt"],
                    "viewCount": video.get("statistics", {}).get(
                        "viewCount", "0"
                    ),
                    "status": video["status"]["privacyStatus"],
                }
            )

        logger.info("Found %d videos", len(results))
        return results

    # ------------------------------------------------------------------
    # Video details
    # ------------------------------------------------------------------

    @retry(max_attempts=3, base_delay=2.0, exceptions=(HttpError,))
    def get_video_details(self, video_id: str) -> dict[str, Any]:
        """Get full details for a specific video.

        Args:
            video_id: The YouTube video ID.

        Returns:
            A dict with ``snippet``, ``statistics``, and ``status`` keys
            taken directly from the YouTube API response.

        Raises:
            ValueError: If the video is not found.
            HttpError: On YouTube API errors (after retries).
        """
        logger.info("Fetching details for video %s", video_id)

        response = (
            self._service.videos()
            .list(
                part="snippet,statistics,status",
                id=video_id,
            )
            .execute()
        )

        if not response.get("items"):
            raise ValueError(f"Video not found: {video_id}")

        video = response["items"][0]
        result: dict[str, Any] = {
            "snippet": video["snippet"],
            "statistics": video.get("statistics", {}),
            "status": video["status"],
        }

        logger.info("Details fetched for video %s", video_id)
        return result

    # ------------------------------------------------------------------
    # Playlist management
    # ------------------------------------------------------------------

    @retry(max_attempts=3, base_delay=2.0, exceptions=(HttpError,))
    def create_playlist(
        self,
        title: str,
        description: str = "",
        visibility: str = "private",
    ) -> str:
        """Create a new playlist on the authenticated channel.

        Args:
            title: Playlist title.
            description: Playlist description.
            visibility: ``"public"``, ``"unlisted"``, or ``"private"``.

        Returns:
            The playlist ID.

        Raises:
            HttpError: On YouTube API errors (after retries).
        """
        logger.info("Creating playlist: title=%r, visibility=%s", title, visibility)

        body: dict[str, Any] = {
            "snippet": {
                "title": title,
                "description": description,
            },
            "status": {
                "privacyStatus": visibility,
            },
        }

        response = (
            self._service.playlists()
            .insert(part="snippet,status", body=body)
            .execute()
        )

        playlist_id: str = response["id"]
        logger.info("Playlist created: playlist_id=%s", playlist_id)
        return playlist_id

    @retry(max_attempts=3, base_delay=2.0, exceptions=(HttpError,))
    def add_to_playlist(
        self,
        playlist_id: str,
        video_id: str,
        position: int | None = None,
    ) -> str:
        """Add a video to a playlist.

        Args:
            playlist_id: The target playlist ID.
            video_id: The YouTube video ID to add.
            position: Zero-based position in the playlist.  ``None`` appends
                to the end.

        Returns:
            The playlist item ID.

        Raises:
            HttpError: On YouTube API errors (after retries).
        """
        logger.info(
            "Adding video %s to playlist %s (position=%s)",
            video_id,
            playlist_id,
            position,
        )

        snippet: dict[str, Any] = {
            "playlistId": playlist_id,
            "resourceId": {
                "kind": "youtube#video",
                "videoId": video_id,
            },
        }

        if position is not None:
            snippet["position"] = position

        body: dict[str, Any] = {"snippet": snippet}

        response = (
            self._service.playlistItems()
            .insert(part="snippet", body=body)
            .execute()
        )

        item_id: str = response["id"]
        logger.info("Video added to playlist: item_id=%s", item_id)
        return item_id

    # ------------------------------------------------------------------
    # End screen (placeholder)
    # ------------------------------------------------------------------

    def set_video_end_screen(
        self,
        video_id: str,
        *,
        promote_video_id: str | None = None,
        subscribe: bool = False,
    ) -> None:
        """Placeholder for setting video end-screen elements.

        The YouTube Data API v3 does **not** support programmatic end-screen
        management.  End screens must be configured through YouTube Studio or
        the YouTube Content ID API (which requires partner access).

        This method is provided as a forward-compatible stub.  When YouTube
        adds end-screen support to the public API, this method will be
        implemented.

        Args:
            video_id: The YouTube video ID.
            promote_video_id: Another video to promote in the end screen.
            subscribe: Whether to include a subscribe element.

        Raises:
            NotImplementedError: Always, until YouTube exposes this in the
                public API.
        """
        logger.warning(
            "set_video_end_screen called for video %s — end screens are not "
            "supported by the YouTube Data API v3. Configure them manually in "
            "YouTube Studio.",
            video_id,
        )
        raise NotImplementedError(
            "YouTube Data API v3 does not support end-screen management. "
            "Use YouTube Studio to configure end screens."
        )
