"""fal.ai-hosted text-to-speech implementation."""

from __future__ import annotations

import os
import tempfile
import uuid
import wave
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import fal_client

from vidmation.config.profiles import VoiceConfig
from vidmation.services.tts.base import TTSProvider
from vidmation.utils.retry import retry

if TYPE_CHECKING:
    from vidmation.config.settings import Settings


# Supported fal.ai TTS model endpoints.
FAL_TTS_MODELS: dict[str, str] = {
    "f5-tts": "fal-ai/f5-tts",
    "kokoro": "fal-ai/kokoro",
}

DEFAULT_MODEL_KEY = "f5-tts"


def _get_audio_duration(path: Path) -> float:
    """Return audio duration in seconds.

    Tries WAV header parsing, falls back to bitrate heuristic.
    """
    suffix = path.suffix.lower()
    if suffix == ".wav":
        with wave.open(str(path), "rb") as wf:
            return wf.getnframes() / float(wf.getframerate())
    return path.stat().st_size * 8 / 128_000


class FalTTS(TTSProvider):
    """Text-to-speech using fal.ai hosted models.

    Supported models:
        - **F5-TTS** (``fal-ai/f5-tts``) -- High-quality, supports reference
          audio for voice cloning.
        - **Kokoro** (``fal-ai/kokoro``) -- Fast, expressive TTS.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        model_key: str = DEFAULT_MODEL_KEY,
    ) -> None:
        super().__init__(settings=settings)
        fal_key = self.settings.fal_key.get_secret_value()
        if not fal_key:
            raise ValueError(
                "fal_key is not configured. "
                "Set VIDMATION_FAL_KEY in your environment."
            )
        # fal_client reads FAL_KEY from the environment.
        os.environ["FAL_KEY"] = fal_key

        self._model_key = model_key
        self._model_id = FAL_TTS_MODELS.get(model_key, model_key)

    # ------------------------------------------------------------------
    # TTSProvider interface
    # ------------------------------------------------------------------

    @retry(max_attempts=3, base_delay=5.0, exceptions=(Exception,))
    def synthesize(
        self,
        text: str,
        voice_config: VoiceConfig,
        output_path: Path,
    ) -> tuple[Path, float]:
        """Generate speech via fal.ai and write to *output_path*.

        The ``voice_config.model`` field can override the default model key.
        ``voice_config.voice_id`` is interpreted as a voice/speaker preset
        name for models that support it.
        """
        model_id = self._resolve_model(voice_config)

        self.logger.info(
            "fal.ai TTS: model=%s, text_len=%d, output=%s",
            model_id,
            len(text),
            output_path,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        input_args = self._build_input(text, voice_config, model_id)

        result: dict[str, Any] = fal_client.subscribe(
            model_id,
            arguments=input_args,
        )

        audio_url = self._extract_audio_url(result)
        self._download_audio(audio_url, output_path)

        duration = _get_audio_duration(output_path)
        self.logger.info(
            "fal.ai TTS complete: %s (%.1fs)", output_path.name, duration
        )
        return output_path, duration

    def list_voices(self) -> list[dict[str, Any]]:
        """Return available fal.ai TTS models as voice entries.

        fal.ai models typically accept reference audio or preset names
        rather than fixed voice IDs.  This returns the model catalogue.
        """
        voices: list[dict[str, Any]] = []
        for key, model_id in FAL_TTS_MODELS.items():
            voices.append(
                {
                    "voice_id": key,
                    "name": key.replace("-", " ").title(),
                    "provider": "fal",
                    "model_id": model_id,
                    "supports_cloning": key == "f5-tts",
                }
            )
        self.logger.info("fal.ai TTS: %d models available", len(voices))
        return voices

    # ------------------------------------------------------------------
    # Voice cloning via F5-TTS reference audio
    # ------------------------------------------------------------------

    @retry(max_attempts=3, base_delay=5.0, exceptions=(Exception,))
    def clone_and_speak(
        self,
        text: str,
        reference_audio: Path,
        output_path: Path,
    ) -> tuple[Path, float]:
        """Clone a voice from reference audio and speak text via F5-TTS.

        F5-TTS supports zero-shot voice cloning by providing a reference
        audio sample and its transcript.

        Args:
            text: The text to speak.
            reference_audio: Path to reference audio (WAV/MP3).
            output_path: Where to write the generated audio.

        Returns:
            ``(audio_path, duration_seconds)`` tuple.
        """
        if not reference_audio.exists():
            raise FileNotFoundError(f"Reference audio not found: {reference_audio}")

        self.logger.info(
            "fal.ai clone-and-speak: ref=%s, text_len=%d",
            reference_audio.name,
            len(text),
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Upload the reference audio to fal for processing.
        ref_url = fal_client.upload_file(str(reference_audio))

        result: dict[str, Any] = fal_client.subscribe(
            FAL_TTS_MODELS["f5-tts"],
            arguments={
                "gen_text": text,
                "ref_audio_url": ref_url,
                "model_type": "F5-TTS",
            },
        )

        audio_url = self._extract_audio_url(result)
        self._download_audio(audio_url, output_path)

        duration = _get_audio_duration(output_path)
        self.logger.info(
            "fal.ai clone-and-speak complete: %s (%.1fs)",
            output_path.name,
            duration,
        )
        return output_path, duration

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_model(self, voice_config: VoiceConfig) -> str:
        """Determine the fal.ai model endpoint from the voice config."""
        if voice_config.model and voice_config.model in FAL_TTS_MODELS:
            return FAL_TTS_MODELS[voice_config.model]
        if voice_config.model:
            return voice_config.model
        return self._model_id

    def _build_input(
        self, text: str, voice_config: VoiceConfig, model_id: str
    ) -> dict[str, Any]:
        """Build model-specific input arguments."""
        if "f5-tts" in model_id:
            params: dict[str, Any] = {
                "gen_text": text,
                "model_type": "F5-TTS",
            }
            if voice_config.speed and voice_config.speed != 1.0:
                params["speed"] = voice_config.speed
            return params

        if "kokoro" in model_id:
            params = {
                "text": text,
            }
            if voice_config.voice_id:
                params["voice"] = voice_config.voice_id
            if voice_config.speed and voice_config.speed != 1.0:
                params["speed"] = voice_config.speed
            return params

        # Generic fallback.
        return {"text": text}

    @staticmethod
    def _extract_audio_url(result: dict[str, Any]) -> str:
        """Extract the audio URL from a fal.ai result payload."""
        # F5-TTS returns {"audio_url": {"url": "..."}}
        audio_data = result.get("audio_url") or result.get("audio") or {}
        if isinstance(audio_data, dict):
            url = audio_data.get("url", "")
        elif isinstance(audio_data, str):
            url = audio_data
        else:
            url = ""

        # Fallback: check top-level "url" key.
        if not url:
            url = result.get("url", "")

        if not url:
            raise RuntimeError(
                f"fal.ai TTS returned no audio URL. Keys: {list(result.keys())}"
            )
        return url

    def _download_audio(self, url: str, output_path: Path) -> None:
        """Download audio from a URL and save to disk."""
        with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as resp:
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)
