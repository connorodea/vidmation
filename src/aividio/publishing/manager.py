"""Unified multi-platform publishing manager.

Orchestrates publishing a single video to one or more platforms
(YouTube, TikTok, Instagram) and tracks results per-platform.

Usage::

    from aividio.publishing.manager import PublishManager

    pm = PublishManager()
    results = pm.publish("video-uuid", platforms=["youtube", "tiktok"])
    # results = {"youtube": {"status": "success", "url": "..."}, ...}
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aividio.db.engine import get_session
from aividio.models.video import Video, VideoStatus

logger = logging.getLogger("aividio.publishing.manager")


class PublishManager:
    """Publish videos to multiple platforms.

    Each platform method returns the public URL on success or raises
    on failure.  The top-level :meth:`publish` method aggregates results
    across all requested platforms and sends a notification when done.
    """

    def publish(
        self,
        video_id: str,
        platforms: list[str],
        schedule_at: datetime | None = None,
    ) -> dict[str, dict[str, str]]:
        """Publish or schedule a video to specified platforms.

        If ``schedule_at`` is provided, the video is scheduled rather than
        published immediately (delegates to :class:`AdvancedScheduler`).

        Args:
            video_id: UUID of the video to publish.
            platforms: List of platform names (``youtube``, ``tiktok``, ``instagram``).
            schedule_at: Optional future datetime for deferred publishing.

        Returns:
            ``{platform: {"status": "success"|"error", "url"|"error": ...}}``
        """
        if schedule_at and schedule_at > datetime.now(timezone.utc):
            return self._schedule_publish(video_id, platforms, schedule_at)

        results: dict[str, dict[str, str]] = {}

        platform_methods = {
            "youtube": self.publish_to_youtube,
            "tiktok": self.publish_to_tiktok,
            "instagram": self.publish_to_instagram,
        }

        for platform in platforms:
            method = platform_methods.get(platform.lower())
            if method is None:
                results[platform] = {
                    "status": "error",
                    "error": f"Unsupported platform: {platform}",
                }
                continue

            try:
                url = method(video_id)
                results[platform] = {"status": "success", "url": url}
                logger.info("Published to %s: %s", platform, url)
            except Exception as exc:
                error_msg = str(exc)[:1000]
                results[platform] = {"status": "error", "error": error_msg}
                logger.error("Failed to publish to %s: %s", platform, exc)

        # Update video status if at least one platform succeeded
        success_count = sum(1 for r in results.values() if r["status"] == "success")
        if success_count > 0:
            self._update_video_status(video_id, results)

        # Send notification
        self._send_notification(video_id, platforms, results)

        return results

    def publish_to_youtube(self, video_id: str) -> str:
        """Publish to YouTube, return the public video URL.

        Uses the existing :class:`YouTubeUploader` with the channel's
        stored OAuth credentials.
        """
        session = get_session()
        try:
            video = session.get(Video, video_id)
            if not video:
                raise ValueError(f"Video '{video_id}' not found")

            if not video.file_path:
                raise ValueError(f"Video '{video_id}' has no rendered file")

            video_path = Path(video.file_path)
            if not video_path.exists():
                raise FileNotFoundError(f"Video file not found: {video_path}")

            # Load channel's OAuth credentials
            from aividio.models.channel import Channel
            channel = session.get(Channel, video.channel_id)
            if not channel or not channel.oauth_token_json:
                raise ValueError(
                    f"Channel has no YouTube OAuth credentials configured. "
                    f"Run 'aividio auth youtube --channel {channel.name if channel else 'unknown'}' first."
                )

            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_info(
                json.loads(channel.oauth_token_json)
            )

            from aividio.services.youtube.uploader import YouTubeUploader
            uploader = YouTubeUploader(credentials=creds)

            yt_video_id = uploader.upload(
                video_path=video_path,
                title=video.title or "Untitled Video",
                description=video.description or "",
                tags=video.tags if isinstance(video.tags, list) else [],
                thumbnail_path=Path(video.thumbnail_path) if video.thumbnail_path else None,
                visibility="public",
            )

            youtube_url = f"https://www.youtube.com/watch?v={yt_video_id}"

            # Update video record
            video.youtube_video_id = yt_video_id
            video.youtube_url = youtube_url
            video.status = VideoStatus.UPLOADED
            session.commit()

            return youtube_url

        finally:
            session.close()

    def publish_to_tiktok(self, video_id: str) -> str:
        """Publish to TikTok via the Content Publishing API.

        This is a placeholder implementation. TikTok's Content Publishing
        API requires:
        1. A registered TikTok developer app
        2. OAuth 2.0 token for the target account
        3. Video upload via their chunked upload flow

        See: https://developers.tiktok.com/doc/content-posting-api-get-started
        """
        session = get_session()
        try:
            video = session.get(Video, video_id)
            if not video:
                raise ValueError(f"Video '{video_id}' not found")

            if not video.file_path:
                raise ValueError(f"Video '{video_id}' has no rendered file")

            # Check for TikTok credentials
            import os
            tiktok_access_token = os.getenv("VIDMATION_TIKTOK_ACCESS_TOKEN", "")
            if not tiktok_access_token:
                raise NotImplementedError(
                    "TikTok publishing requires VIDMATION_TIKTOK_ACCESS_TOKEN. "
                    "Set up TikTok Content Publishing API credentials first."
                )

            # Step 1: Initialize upload
            import httpx

            # Create video upload session
            init_response = httpx.post(
                "https://open.tiktokapis.com/v2/post/publish/video/init/",
                headers={
                    "Authorization": f"Bearer {tiktok_access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "post_info": {
                        "title": (video.title or "")[:150],
                        "privacy_level": "PUBLIC_TO_EVERYONE",
                        "disable_duet": False,
                        "disable_comment": False,
                        "disable_stitch": False,
                    },
                    "source_info": {
                        "source": "FILE_UPLOAD",
                        "video_size": Path(video.file_path).stat().st_size,
                    },
                },
                timeout=30.0,
            )
            init_response.raise_for_status()
            init_data = init_response.json()

            upload_url = init_data.get("data", {}).get("upload_url")
            publish_id = init_data.get("data", {}).get("publish_id")

            if not upload_url:
                raise RuntimeError(f"TikTok upload init failed: {init_data}")

            # Step 2: Upload the video file
            with open(video.file_path, "rb") as f:
                upload_response = httpx.put(
                    upload_url,
                    content=f.read(),
                    headers={"Content-Type": "video/mp4"},
                    timeout=300.0,
                )
                upload_response.raise_for_status()

            logger.info("TikTok upload complete, publish_id=%s", publish_id)

            # TikTok doesn't return a direct URL immediately;
            # the video goes through processing
            return f"https://www.tiktok.com/@user/video/{publish_id}"

        finally:
            session.close()

    def publish_to_instagram(self, video_id: str) -> str:
        """Publish to Instagram Reels via the Meta Graph API.

        This is a placeholder implementation. Instagram Reels publishing
        requires:
        1. A Meta/Facebook developer app
        2. Instagram Professional Account connected
        3. Graph API access token with ``instagram_content_publish`` permission

        See: https://developers.facebook.com/docs/instagram-api/guides/content-publishing
        """
        session = get_session()
        try:
            video = session.get(Video, video_id)
            if not video:
                raise ValueError(f"Video '{video_id}' not found")

            if not video.file_path:
                raise ValueError(f"Video '{video_id}' has no rendered file")

            import os
            ig_access_token = os.getenv("VIDMATION_INSTAGRAM_ACCESS_TOKEN", "")
            ig_account_id = os.getenv("VIDMATION_INSTAGRAM_ACCOUNT_ID", "")

            if not ig_access_token or not ig_account_id:
                raise NotImplementedError(
                    "Instagram publishing requires VIDMATION_INSTAGRAM_ACCESS_TOKEN and "
                    "VIDMATION_INSTAGRAM_ACCOUNT_ID. Set up Meta Graph API credentials first."
                )

            import httpx

            # The video must be hosted at a public URL for Instagram's API.
            # In production, this would upload to a CDN/S3 first.
            video_url = os.getenv("VIDMATION_PUBLIC_BASE_URL", "")
            if not video_url:
                raise NotImplementedError(
                    "Instagram publishing requires VIDMATION_PUBLIC_BASE_URL to serve "
                    "video files publicly. Configure a CDN or public file server."
                )

            public_video_url = f"{video_url.rstrip('/')}/output/{Path(video.file_path).name}"

            # Step 1: Create media container
            container_response = httpx.post(
                f"https://graph.facebook.com/v19.0/{ig_account_id}/media",
                params={
                    "media_type": "REELS",
                    "video_url": public_video_url,
                    "caption": (video.description or video.title or "")[:2200],
                    "access_token": ig_access_token,
                },
                timeout=30.0,
            )
            container_response.raise_for_status()
            container_id = container_response.json().get("id")

            if not container_id:
                raise RuntimeError(
                    f"Instagram container creation failed: {container_response.json()}"
                )

            # Step 2: Publish the container
            publish_response = httpx.post(
                f"https://graph.facebook.com/v19.0/{ig_account_id}/media_publish",
                params={
                    "creation_id": container_id,
                    "access_token": ig_access_token,
                },
                timeout=60.0,
            )
            publish_response.raise_for_status()
            media_id = publish_response.json().get("id")

            logger.info("Instagram Reel published, media_id=%s", media_id)

            # Construct permalink
            permalink_response = httpx.get(
                f"https://graph.facebook.com/v19.0/{media_id}",
                params={
                    "fields": "permalink",
                    "access_token": ig_access_token,
                },
                timeout=10.0,
            )
            permalink = permalink_response.json().get(
                "permalink", f"https://www.instagram.com/reel/{media_id}/"
            )

            return permalink

        finally:
            session.close()

    def get_publish_status(self, video_id: str) -> dict[str, Any]:
        """Get publishing status across all platforms for a video.

        Returns a dict with platform-level status and URLs.
        """
        session = get_session()
        try:
            video = session.get(Video, video_id)
            if not video:
                return {"error": "Video not found"}

            status: dict[str, Any] = {
                "video_id": video_id,
                "video_status": video.status.value if video.status else "unknown",
                "platforms": {},
            }

            # YouTube
            if video.youtube_video_id:
                status["platforms"]["youtube"] = {
                    "status": "published",
                    "video_id": video.youtube_video_id,
                    "url": video.youtube_url or f"https://www.youtube.com/watch?v={video.youtube_video_id}",
                }
            else:
                status["platforms"]["youtube"] = {"status": "not_published"}

            # TikTok and Instagram status would come from their APIs
            # or from a local publish_results table in a future version
            status["platforms"]["tiktok"] = {"status": "not_configured"}
            status["platforms"]["instagram"] = {"status": "not_configured"}

            return status
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _schedule_publish(
        self,
        video_id: str,
        platforms: list[str],
        schedule_at: datetime,
    ) -> dict[str, dict[str, str]]:
        """Delegate to AdvancedScheduler for deferred publishing."""
        from aividio.scheduling.advanced import AdvancedScheduler

        scheduler = AdvancedScheduler()
        schedule = scheduler.schedule_video(
            video_id=video_id,
            publish_at=schedule_at,
            platforms=platforms,
        )

        return {
            platform: {
                "status": "scheduled",
                "schedule_id": schedule.id,
                "publish_at": schedule_at.isoformat(),
            }
            for platform in platforms
        }

    def _update_video_status(
        self, video_id: str, results: dict[str, dict[str, str]]
    ) -> None:
        """Update the video record after publishing."""
        session = get_session()
        try:
            video = session.get(Video, video_id)
            if video and video.status != VideoStatus.UPLOADED:
                # Only update to UPLOADED if YouTube succeeded (primary platform)
                yt_result = results.get("youtube", {})
                if yt_result.get("status") == "success" and yt_result.get("url"):
                    video.status = VideoStatus.UPLOADED
                    video.youtube_url = yt_result["url"]
                    session.commit()
        except Exception:
            session.rollback()
            logger.error("Failed to update video status after publish", exc_info=True)
        finally:
            session.close()

    def _send_notification(
        self,
        video_id: str,
        platforms: list[str],
        results: dict[str, dict[str, str]],
    ) -> None:
        """Send a publish-complete notification."""
        try:
            from aividio.notifications.manager import NotificationManager
            notifier = NotificationManager()
            notifier.notify_publish_complete(
                video_id=video_id,
                platforms=platforms,
                results=results,
            )
        except Exception:
            logger.debug("Notification send failed", exc_info=True)
