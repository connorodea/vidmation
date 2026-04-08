"""YouTube multi-channel manager — connect, disconnect, publish to any channel.

Provides a high-level interface for SaaS multi-channel YouTube operations.
Each channel stores its own OAuth credentials in the database so the system
can programmatically publish to ANY connected channel.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from vidmation.config.settings import Settings, get_settings

logger = logging.getLogger("vidmation.services.youtube.manager")


class YouTubeChannelManager:
    """Manage multiple YouTube channel connections and publishing.

    This class orchestrates OAuth flows, credential storage, and video
    publishing across all connected channels.  It is the primary entry
    point for multi-channel operations in a SaaS context.

    Args:
        settings: Application settings.  Defaults to the cached singleton.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def _client_secret_path(self) -> Path:
        return self._settings.data_dir / "client_secret.json"

    # ------------------------------------------------------------------
    # Channel connection lifecycle
    # ------------------------------------------------------------------

    def connect_channel(self, channel_name: str, client_secret_path: Path | None = None) -> dict:
        """Run the OAuth flow for a channel and store credentials in the DB.

        After OAuth completes, the YouTube channel info is fetched and
        persisted on the channel record.

        Args:
            channel_name: The name of an existing channel in the database.
            client_secret_path: Path to the Google OAuth client secret
                JSON file.  Defaults to ``data/client_secret.json``.

        Returns:
            A dict with YouTube channel info (``id``, ``title``,
            ``subscriber_count``, ``video_count``, ``thumbnail_url``).

        Raises:
            ValueError: If the channel does not exist.
            FileNotFoundError: If the client secret file is missing.
        """
        from vidmation.db.engine import get_session, init_db
        from vidmation.db.repos import ChannelRepo
        from vidmation.services.youtube.auth import (
            fetch_youtube_channel_info,
            get_credentials_for_channel,
        )

        secret_path = client_secret_path or self._client_secret_path
        init_db()

        session = get_session()
        try:
            repo = ChannelRepo(session)
            channel = repo.get_by_name(channel_name)
            if channel is None:
                raise ValueError(f"Channel '{channel_name}' not found in the database.")

            logger.info("Starting OAuth flow for channel '%s' (%s)", channel_name, channel.id[:8])

            creds = get_credentials_for_channel(
                channel_id=channel.id,
                client_secret_path=secret_path,
            )

            # Fetch and store YouTube channel info
            ch_info = fetch_youtube_channel_info(creds)
            if ch_info:
                channel.youtube_channel_id = ch_info["id"]
                channel.youtube_channel_title = ch_info["title"]
                session.commit()
                logger.info(
                    "Connected channel '%s' to YouTube channel '%s' (%s)",
                    channel_name,
                    ch_info["title"],
                    ch_info["id"],
                )
            else:
                logger.warning("OAuth succeeded but no YouTube channel found for the Google account.")

            return ch_info

        finally:
            session.close()

    def disconnect_channel(self, channel_name: str) -> None:
        """Remove the stored OAuth token for a channel.

        The channel record remains in the database but its YouTube
        connection is severed.

        Args:
            channel_name: The name of the channel to disconnect.

        Raises:
            ValueError: If the channel does not exist.
        """
        from vidmation.db.engine import get_session, init_db
        from vidmation.db.repos import ChannelRepo

        init_db()
        session = get_session()
        try:
            repo = ChannelRepo(session)
            channel = repo.get_by_name(channel_name)
            if channel is None:
                raise ValueError(f"Channel '{channel_name}' not found in the database.")

            channel.oauth_token_json = None
            channel.oauth_connected_at = None
            channel.youtube_channel_id = None
            channel.youtube_channel_title = None
            session.commit()

            logger.info("Disconnected YouTube from channel '%s'", channel_name)
        finally:
            session.close()

    def list_connected_channels(self) -> list[dict[str, Any]]:
        """Return summary dicts for all channels that have YouTube connections.

        Returns:
            A list of dicts, each containing ``name``, ``channel_id``,
            ``youtube_channel_id``, ``youtube_channel_title``,
            ``connected_at``, and ``is_active``.
        """
        from vidmation.db.engine import get_session, init_db
        from vidmation.db.repos import ChannelRepo

        init_db()
        session = get_session()
        try:
            repo = ChannelRepo(session)
            all_channels = repo.list_all(active_only=False)

            results: list[dict[str, Any]] = []
            for ch in all_channels:
                if ch.is_youtube_connected:
                    results.append({
                        "name": ch.name,
                        "channel_id": ch.id,
                        "youtube_channel_id": ch.youtube_channel_id,
                        "youtube_channel_title": ch.youtube_channel_title,
                        "connected_at": (
                            ch.oauth_connected_at.isoformat()
                            if ch.oauth_connected_at
                            else None
                        ),
                        "is_active": ch.is_active,
                    })

            return results
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def publish_to_channel(
        self,
        channel_name: str,
        video_path: Path | str,
        title: str,
        description: str = "",
        tags: list[str] | None = None,
        category_id: str = "22",
        thumbnail_path: Path | str | None = None,
        visibility: str = "private",
        publish_at: datetime | None = None,
    ) -> str:
        """Upload and publish a video to a specific connected channel.

        Args:
            channel_name: The name of the channel to publish to.
            video_path: Path to the video file.
            title: Video title.
            description: Video description.
            tags: Optional list of tags.
            category_id: YouTube category ID (default ``"22"``).
            thumbnail_path: Optional path to a thumbnail image.
            visibility: ``"public"``, ``"unlisted"``, or ``"private"``.
            publish_at: Optional scheduled publish time (UTC).

        Returns:
            The YouTube video ID.

        Raises:
            ValueError: If the channel is not found or not connected.
            FileNotFoundError: If the video or client secret file is missing.
        """
        from vidmation.db.engine import get_session, init_db
        from vidmation.db.repos import ChannelRepo
        from vidmation.services.youtube.auth import get_credentials_for_channel
        from vidmation.services.youtube.uploader import YouTubeUploader

        video_path = Path(video_path)
        thumb = Path(thumbnail_path) if thumbnail_path else None

        init_db()
        session = get_session()
        try:
            repo = ChannelRepo(session)
            channel = repo.get_by_name(channel_name)
            if channel is None:
                raise ValueError(f"Channel '{channel_name}' not found.")
            if not channel.is_youtube_connected:
                raise ValueError(
                    f"Channel '{channel_name}' is not connected to YouTube. "
                    f"Run: vidmation youtube setup --channel {channel_name}"
                )

            creds = get_credentials_for_channel(
                channel_id=channel.id,
                client_secret_path=self._client_secret_path,
            )
            uploader = YouTubeUploader(credentials=creds)

            logger.info(
                "Publishing to channel '%s' (%s): title=%r",
                channel_name,
                channel.youtube_channel_id or "?",
                title,
            )

            if publish_at:
                video_id = uploader.upload_with_schedule(
                    video_path=video_path,
                    title=title,
                    description=description,
                    tags=tags,
                    category_id=category_id,
                    thumbnail_path=thumb,
                    publish_at=publish_at,
                )
            else:
                video_id = uploader.upload(
                    video_path=video_path,
                    title=title,
                    description=description,
                    tags=tags,
                    category_id=category_id,
                    thumbnail_path=thumb,
                    visibility=visibility,
                )

            logger.info(
                "Published to '%s': video_id=%s",
                channel_name,
                video_id,
            )
            return video_id

        finally:
            session.close()

    def publish_to_all_channels(
        self,
        video_path: Path | str,
        title: str,
        description: str = "",
        tags: list[str] | None = None,
        category_id: str = "22",
        thumbnail_path: Path | str | None = None,
        visibility: str = "private",
        publish_at: datetime | None = None,
        active_only: bool = True,
    ) -> dict[str, str]:
        """Publish the same video to ALL connected YouTube channels.

        Args:
            video_path: Path to the video file.
            title: Video title.
            description: Video description.
            tags: Optional list of tags.
            category_id: YouTube category ID.
            thumbnail_path: Optional thumbnail image path.
            visibility: Default visibility for all uploads.
            publish_at: Optional scheduled publish time (UTC).
            active_only: If True (default), skip inactive channels.

        Returns:
            A dict mapping channel name to YouTube video ID.  Channels
            that fail are logged but do not prevent other channels from
            being published to.
        """
        connected = self.list_connected_channels()

        if active_only:
            connected = [c for c in connected if c["is_active"]]

        if not connected:
            logger.warning("No connected channels found — nothing to publish.")
            return {}

        logger.info(
            "Publishing to %d connected channels: %s",
            len(connected),
            ", ".join(c["name"] for c in connected),
        )

        results: dict[str, str] = {}

        for ch in connected:
            ch_name = ch["name"]
            try:
                video_id = self.publish_to_channel(
                    channel_name=ch_name,
                    video_path=video_path,
                    title=title,
                    description=description,
                    tags=tags,
                    category_id=category_id,
                    thumbnail_path=thumbnail_path,
                    visibility=visibility,
                    publish_at=publish_at,
                )
                results[ch_name] = video_id
                logger.info("Published to '%s': %s", ch_name, video_id)
            except Exception as exc:
                logger.error(
                    "Failed to publish to '%s': %s",
                    ch_name,
                    exc,
                    exc_info=True,
                )
                results[ch_name] = f"ERROR: {exc}"

        successful = sum(1 for v in results.values() if not v.startswith("ERROR:"))
        logger.info(
            "Multi-channel publish complete: %d/%d succeeded",
            successful,
            len(connected),
        )

        return results
