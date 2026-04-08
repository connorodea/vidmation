"""YouTube Analytics fetcher - pulls performance metrics from the YouTube API."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from vidmation.db.engine import get_session
from vidmation.models.analytics import VideoAnalytics
from vidmation.models.channel import Channel
from vidmation.models.video import Video, VideoStatus

logger = logging.getLogger("vidmation.analytics.youtube")


class YouTubeAnalyticsFetcher:
    """Fetches video and channel performance metrics from YouTube APIs.

    Uses the YouTube Data API v3 for basic metrics and the YouTube
    Analytics API for detailed engagement data. Requires existing OAuth
    credentials stored on the Channel model.
    """

    def __init__(self) -> None:
        self._yt_service_cache: dict[str, Any] = {}

    def _get_youtube_service(self, channel: Channel) -> Any:
        """Build a YouTube API service from stored OAuth credentials."""
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        cache_key = channel.id
        if cache_key in self._yt_service_cache:
            return self._yt_service_cache[cache_key]

        if not channel.oauth_token_json:
            raise ValueError(
                f"Channel '{channel.name}' has no OAuth credentials. "
                "Run the YouTube auth flow first."
            )

        creds_data = json.loads(channel.oauth_token_json)
        creds = Credentials.from_authorized_user_info(creds_data)

        # Refresh if expired
        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())

        service = build("youtube", "v3", credentials=creds, cache_discovery=False)
        self._yt_service_cache[cache_key] = service
        return service

    def _get_analytics_service(self, channel: Channel) -> Any:
        """Build a YouTube Analytics API service."""
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        if not channel.oauth_token_json:
            raise ValueError(
                f"Channel '{channel.name}' has no OAuth credentials."
            )

        creds_data = json.loads(channel.oauth_token_json)
        creds = Credentials.from_authorized_user_info(creds_data)

        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())

        return build(
            "youtubeAnalytics", "v2",
            credentials=creds,
            cache_discovery=False,
        )

    def fetch_video_stats(self, youtube_video_id: str, channel: Channel) -> dict[str, Any]:
        """Pull stats for a single video from the YouTube Data API.

        Args:
            youtube_video_id: The YouTube video ID (e.g. ``dQw4w9WgXcQ``).
            channel: The Channel object with OAuth credentials.

        Returns:
            Dict with view counts, likes, comments, and other metrics.
        """
        service = self._get_youtube_service(channel)

        # Basic statistics from Data API
        response = (
            service.videos()
            .list(
                part="statistics,contentDetails",
                id=youtube_video_id,
            )
            .execute()
        )

        if not response.get("items"):
            logger.warning("No data returned for video %s", youtube_video_id)
            return {}

        item = response["items"][0]
        stats = item.get("statistics", {})
        content = item.get("contentDetails", {})

        result: dict[str, Any] = {
            "youtube_video_id": youtube_video_id,
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
            "duration_iso": content.get("duration", ""),
        }

        # Try to get analytics data (watch time, CTR, etc.)
        try:
            analytics = self._fetch_video_analytics(youtube_video_id, channel)
            result.update(analytics)
        except Exception as exc:
            logger.warning(
                "Could not fetch analytics for %s: %s",
                youtube_video_id, exc,
            )

        return result

    def _fetch_video_analytics(
        self, youtube_video_id: str, channel: Channel
    ) -> dict[str, Any]:
        """Fetch detailed analytics for a video from the Analytics API."""
        analytics_service = self._get_analytics_service(channel)

        # Get the last 90 days of data
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start_date = (
            datetime.now(timezone.utc)
            - __import__("datetime").timedelta(days=90)
        ).strftime("%Y-%m-%d")

        response = (
            analytics_service.reports()
            .query(
                ids=f"channel=={channel.youtube_channel_id}",
                startDate=start_date,
                endDate=end_date,
                metrics=(
                    "views,estimatedMinutesWatched,averageViewDuration,"
                    "averageViewPercentage,annotationClickThroughRate,"
                    "impressions,subscribersGained,shares"
                ),
                filters=f"video=={youtube_video_id}",
                dimensions="video",
            )
            .execute()
        )

        if not response.get("rows"):
            return {}

        row = response["rows"][0]
        headers = [col["name"] for col in response.get("columnHeaders", [])]
        data = dict(zip(headers, row))

        return {
            "watch_time_hours": round(
                float(data.get("estimatedMinutesWatched", 0)) / 60, 2
            ),
            "avg_view_duration_seconds": float(
                data.get("averageViewDuration", 0)
            ),
            "avg_view_percentage": float(
                data.get("averageViewPercentage", 0)
            ),
            "click_through_rate": float(
                data.get("annotationClickThroughRate", 0)
            ),
            "impressions": int(data.get("impressions", 0)),
            "subscriber_gain": int(data.get("subscribersGained", 0)),
            "shares": int(data.get("shares", 0)),
        }

    def fetch_channel_stats(self, channel: Channel) -> dict[str, Any]:
        """Pull channel-level statistics.

        Args:
            channel: The Channel object with OAuth credentials.

        Returns:
            Dict with subscriber count, total views, video count, etc.
        """
        service = self._get_youtube_service(channel)

        response = (
            service.channels()
            .list(
                part="statistics,snippet",
                id=channel.youtube_channel_id,
            )
            .execute()
        )

        if not response.get("items"):
            logger.warning(
                "No data returned for channel %s", channel.youtube_channel_id
            )
            return {}

        item = response["items"][0]
        stats = item.get("statistics", {})
        snippet = item.get("snippet", {})

        return {
            "channel_id": channel.youtube_channel_id,
            "channel_name": snippet.get("title", channel.name),
            "subscribers": int(stats.get("subscriberCount", 0)),
            "total_views": int(stats.get("viewCount", 0)),
            "total_videos": int(stats.get("videoCount", 0)),
        }

    def sync_video(self, video: Video, channel: Channel) -> VideoAnalytics | None:
        """Fetch and store analytics for a single video.

        Returns the saved VideoAnalytics row, or None if fetch fails.
        """
        if not video.youtube_video_id:
            logger.debug("Video %s has no YouTube ID, skipping", video.id[:8])
            return None

        try:
            stats = self.fetch_video_stats(video.youtube_video_id, channel)
        except Exception as exc:
            logger.error(
                "Failed to fetch stats for video %s: %s",
                video.id[:8], exc,
            )
            return None

        if not stats:
            return None

        session = get_session()
        try:
            analytics = VideoAnalytics(
                video_id=video.id,
                fetched_at=datetime.now(timezone.utc),
                views=stats.get("views", 0),
                likes=stats.get("likes", 0),
                comments=stats.get("comments", 0),
                shares=stats.get("shares", 0),
                watch_time_hours=stats.get("watch_time_hours", 0.0),
                avg_view_duration_seconds=stats.get("avg_view_duration_seconds", 0.0),
                avg_view_percentage=stats.get("avg_view_percentage", 0.0),
                click_through_rate=stats.get("click_through_rate", 0.0),
                impressions=stats.get("impressions", 0),
                subscriber_gain=stats.get("subscriber_gain", 0),
            )
            session.add(analytics)
            session.commit()
            session.refresh(analytics)

            logger.info(
                "Synced analytics for video %s: %d views, %d likes",
                video.id[:8], analytics.views, analytics.likes,
            )
            return analytics
        except Exception:
            session.rollback()
            logger.exception("Failed to save analytics for video %s", video.id[:8])
            return None
        finally:
            session.close()

    def sync_all_videos(self) -> dict[str, Any]:
        """Update analytics for all uploaded videos across all channels.

        Returns a summary of the sync operation.
        """
        session = get_session()
        try:
            # Get all channels with OAuth credentials
            channels_stmt = select(Channel).where(
                Channel.oauth_token_json.isnot(None),
                Channel.is_active.is_(True),
            )
            channels = list(session.scalars(channels_stmt).all())

            synced = 0
            failed = 0
            skipped = 0

            for channel in channels:
                videos_stmt = (
                    select(Video)
                    .where(
                        Video.channel_id == channel.id,
                        Video.status == VideoStatus.UPLOADED,
                        Video.youtube_video_id.isnot(None),
                    )
                )
                videos = list(session.scalars(videos_stmt).all())

                for video in videos:
                    result = self.sync_video(video, channel)
                    if result:
                        synced += 1
                    elif video.youtube_video_id:
                        failed += 1
                    else:
                        skipped += 1

            summary = {
                "channels_processed": len(channels),
                "videos_synced": synced,
                "videos_failed": failed,
                "videos_skipped": skipped,
            }
            logger.info("Sync complete: %s", summary)
            return summary
        finally:
            session.close()
