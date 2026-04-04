"""ElevenLabs text-to-speech implementation."""

from __future__ import annotations

import wave
from pathlib import Path
from typing import TYPE_CHECKING

from elevenlabs import ElevenLabs
from elevenlabs.core import ApiError

from vidmation.config.profiles import VoiceConfig
from vidmation.services.tts.base import TTSProvider
from vidmation.utils.retry import retry

if TYPE_CHECKING:
    from vidmation.config.settings import Settings


def _get_mp3_duration(path: Path) -> float:
    """Estimate MP3 duration from file size and assumed bitrate.

    For a more precise measurement, consider using mutagen or pydub.
    This is a fast heuristic: ``file_bytes * 8 / bitrate_bps``.
    """
    size_bytes = path.stat().st_size
    # ElevenLabs default output is ~128 kbps MP3
    return size_bytes * 8 / 128_000


def _get_wav_duration(path: Path) -> float:
    """Get exact WAV duration from the header."""
    with wave.open(str(path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)


def _get_audio_duration(path: Path) -> float:
    """Return audio duration in seconds, choosing strategy by extension."""
    suffix = path.suffix.lower()
    if suffix == ".wav":
        return _get_wav_duration(path)
    # Default heuristic for mp3/other
    return _get_mp3_duration(path)


class ElevenLabsTTS(TTSProvider):
    """Generate voice-over audio via ElevenLabs API."""

    DEFAULT_MODEL = "eleven_multilingual_v2"

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__(settings=settings)
        api_key = self.settings.elevenlabs_api_key.get_secret_value()
        if not api_key:
            raise ValueError(
                "elevenlabs_api_key is not configured. "
                "Set VIDMATION_ELEVENLABS_API_KEY in your environment."
            )
        self._client = ElevenLabs(api_key=api_key)

    @retry(max_attempts=3, base_delay=2.0, exceptions=(ApiError, ConnectionError))
    def synthesize(
        self,
        text: str,
        voice_config: VoiceConfig,
        output_path: Path,
    ) -> tuple[Path, float]:
        """Synthesize speech with ElevenLabs and write to *output_path*."""
        self.logger.info(
            "ElevenLabs TTS: voice_id=%s, text_len=%d, output=%s",
            voice_config.voice_id,
            len(text),
            output_path,
        )

        if not voice_config.voice_id:
            raise ValueError("voice_config.voice_id is required for ElevenLabs TTS")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        audio_iterator = self._client.text_to_speech.convert(
            voice_id=voice_config.voice_id,
            text=text,
            model_id=voice_config.model or self.DEFAULT_MODEL,
            voice_settings={
                "stability": voice_config.stability,
                "similarity_boost": voice_config.similarity_boost,
            },
        )

        # Write streamed bytes to disk.
        with open(output_path, "wb") as f:
            for chunk in audio_iterator:
                f.write(chunk)

        duration = _get_audio_duration(output_path)

        self.logger.info(
            "ElevenLabs TTS complete: %s (%.1fs)", output_path.name, duration
        )
        return output_path, duration

    @retry(max_attempts=2, base_delay=1.0, exceptions=(ApiError, ConnectionError))
    def list_voices(self) -> list[dict]:
        """Fetch all available ElevenLabs voices."""
        response = self._client.voices.get_all()
        voices = []
        for voice in response.voices:
            voices.append(
                {
                    "voice_id": voice.voice_id,
                    "name": voice.name,
                    "category": getattr(voice, "category", None),
                    "labels": getattr(voice, "labels", {}),
                    "preview_url": getattr(voice, "preview_url", None),
                }
            )
        self.logger.info("Retrieved %d voices from ElevenLabs", len(voices))
        return voices
