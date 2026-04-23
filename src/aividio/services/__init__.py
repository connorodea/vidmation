"""Service layer — API integrations for video production pipeline.

Each sub-package exposes a factory function that returns the correct
implementation based on application settings or an explicit provider name.
"""

from __future__ import annotations

from aividio.services.base import BaseService
from aividio.services.captions.whisper import WhisperCaptionGenerator
from aividio.services.imagegen import create_image_generator
from aividio.services.media import create_media_provider
from aividio.services.scriptgen import create_script_generator
from aividio.services.tts import create_tts_provider
from aividio.services.youtube.auth import get_credentials
from aividio.services.youtube.uploader import YouTubeUploader

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
