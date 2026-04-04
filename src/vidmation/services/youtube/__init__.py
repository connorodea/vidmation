"""YouTube service — OAuth authentication and video upload."""

from __future__ import annotations

from vidmation.services.youtube.auth import get_credentials
from vidmation.services.youtube.uploader import YouTubeUploader

__all__ = ["get_credentials", "YouTubeUploader"]
