"""YouTube service — OAuth authentication, video upload, and metadata generation."""

from __future__ import annotations

from vidmation.services.youtube.auth import (
    fetch_youtube_channel_info,
    get_credentials,
    get_credentials_for_channel,
    store_credentials_for_channel,
)
from vidmation.services.youtube.manager import YouTubeChannelManager
from vidmation.services.youtube.metadata import YouTubeMetadataGenerator
from vidmation.services.youtube.uploader import YouTubeUploader

__all__ = [
    "fetch_youtube_channel_info",
    "get_credentials",
    "get_credentials_for_channel",
    "store_credentials_for_channel",
    "YouTubeChannelManager",
    "YouTubeMetadataGenerator",
    "YouTubeUploader",
]
