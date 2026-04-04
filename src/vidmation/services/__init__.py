"""Service layer — API integrations for video production pipeline.

Each sub-package exposes a factory function that returns the correct
implementation based on application settings or an explicit provider name.
"""

from __future__ import annotations

from vidmation.services.base import BaseService
from vidmation.services.captions.whisper import WhisperCaptionGenerator
from vidmation.services.imagegen import create_image_generator
from vidmation.services.media import create_media_provider
from vidmation.services.scriptgen import create_script_generator
from vidmation.services.tts import create_tts_provider
from vidmation.services.youtube.auth import get_credentials
from vidmation.services.youtube.uploader import YouTubeUploader

__all__ = [
    "BaseService",
    "WhisperCaptionGenerator",
    "create_image_generator",
    "create_media_provider",
    "create_script_generator",
    "create_tts_provider",
    "get_credentials",
    "YouTubeUploader",
]
