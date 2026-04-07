"""YouTube service — OAuth authentication, video upload, and metadata generation."""

from __future__ import annotations

from vidmation.services.youtube.auth import get_credentials
from vidmation.services.youtube.metadata import YouTubeMetadataGenerator
from vidmation.services.youtube.uploader import YouTubeUploader

__all__ = ["get_credentials", "YouTubeMetadataGenerator", "YouTubeUploader"]
