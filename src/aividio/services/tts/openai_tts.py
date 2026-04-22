"""OpenAI TTS implementation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import openai

from aividio.config.profiles import VoiceConfig
from aividio.services.tts.base import TTSProvider
from aividio.utils.retry import retry

if TYPE_CHECKING:
    from aividio.config.settings import Settings

# OpenAI TTS available voices.
OPENAI_VOICES = ("alloy", "echo", "fable", "onyx", "nova", "shimmer")
DEFAULT_VOICE = "nova"


def _estimate_tts_duration(text: str, speed: float = 1.0) -> float:
    """Estimate speech duration from word count (~150 wpm at 1x speed)."""
    word_count = len(text.split())
    return (word_count / 150) * 60 / speed


class OpenAITTS(TTSProvider):
    """Generate voice-over audio via OpenAI TTS API."""

    MODEL = "tts-1-hd"

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__(settings=settings)
        api_key = self.settings.openai_api_key.get_secret_value()
        if not api_key:
            raise ValueError(
                "openai_api_key is not configured. "
                "Set VIDMATION_OPENAI_API_KEY in your environment."
            )
        self._client = openai.OpenAI(api_key=api_key)

    def _resolve_voice(self, voice_config: VoiceConfig) -> str:
        """Map VoiceConfig to a valid OpenAI voice name.

        If the profile's voice_id matches one of the OpenAI voices, use it
        directly; otherwise fall back to the default.
        """
        if voice_config.voice_id and voice_config.voice_id in OPENAI_VOICES:
            return voice_config.voice_id
        self.logger.debug(
            "voice_id=%r not in OpenAI voices; using default=%s",
            voice_config.voice_id,
            DEFAULT_VOICE,
        )
        return DEFAULT_VOICE

    @retry(max_attempts=3, base_delay=2.0, exceptions=(openai.APIError,))
    def synthesize(
        self,
        text: str,
        voice_config: VoiceConfig,
        output_path: Path,
    ) -> tuple[Path, float]:
        """Synthesize speech with OpenAI TTS and write to *output_path*."""
        voice = self._resolve_voice(voice_config)
        self.logger.info(
            "OpenAI TTS: voice=%s, text_len=%d, output=%s",
            voice,
            len(text),
            output_path,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        response = self._client.audio.speech.create(
            model=self.MODEL,
            voice=voice,
            input=text,
            speed=voice_config.speed,
            response_format="mp3",
        )

        response.stream_to_file(str(output_path))

        # Estimate duration from text (OpenAI TTS doesn't return duration).
        duration = _estimate_tts_duration(text, voice_config.speed)

        self.logger.info(
            "OpenAI TTS complete: %s (~%.1fs estimated)", output_path.name, duration
        )
        return output_path, duration

    def list_voices(self) -> list[dict]:
        """Return the fixed set of OpenAI TTS voices."""
        return [
            {"voice_id": v, "name": v.title(), "provider": "openai"}
            for v in OPENAI_VOICES
        ]
