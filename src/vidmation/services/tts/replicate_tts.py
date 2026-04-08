"""Replicate-hosted text-to-speech implementation."""

from __future__ import annotations

import wave
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import replicate
from replicate.exceptions import ReplicateError

from vidmation.config.profiles import VoiceConfig
from vidmation.services.tts.base import TTSProvider
from vidmation.utils.retry import retry

if TYPE_CHECKING:
    from vidmation.config.settings import Settings


# Supported model catalogue with their Replicate identifiers.
REPLICATE_TTS_MODELS: dict[str, str] = {
    "parler-tts": "cjwbw/parler-tts:ea40e856f3561e6d0e0a3b8b3e2dbee8ae07df9e48e7627ab1a2b95c37e131e0",
    "xtts-v2": "lucataco/xtts-v2:684bc3855b37866c0c65add2ff39c78f3dea3f4ff103a436465326e0f438d55e",
    "tortoise-tts": "jbetker/tortoise-tts:e9658de4b325863c4fcdc12d94bb7c9b54f1fb233e21df2bbd50b0c5da863647",
    "speech-01-turbo": "minimax/speech-01-turbo",
}

DEFAULT_MODEL_KEY = "xtts-v2"


def _get_audio_duration(path: Path) -> float:
    """Return audio duration in seconds.

    Attempts WAV header parsing first, then falls back to a bitrate
    heuristic for MP3/other formats.
    """
    suffix = path.suffix.lower()
    if suffix == ".wav":
        with wave.open(str(path), "rb") as wf:
            return wf.getnframes() / float(wf.getframerate())
    # Fallback heuristic for MP3 (~128 kbps).
    return path.stat().st_size * 8 / 128_000


class ReplicateTTS(TTSProvider):
    """Text-to-speech using Replicate-hosted models.

    Supported models:
        - **parler-tts** (``cjwbw/parler-tts``) -- Free-tier quality, fast.
        - **xtts-v2** (``lucataco/xtts-v2``) -- Voice-cloning capable.
        - **tortoise-tts** (``jbetker/tortoise-tts``) -- High quality, slow.
        - **speech-01-turbo** (``minimax/speech-01-turbo``) -- Fast, multilingual.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        model_key: str = DEFAULT_MODEL_KEY,
    ) -> None:
        super().__init__(settings=settings)
        api_token = self.settings.replicate_api_token.get_secret_value()
        if not api_token:
            raise ValueError(
                "replicate_api_token is not configured. "
                "Set VIDMATION_REPLICATE_API_TOKEN in your environment."
            )
        self._client = replicate.Client(api_token=api_token)
        self._model_key = model_key
        self._model_id = REPLICATE_TTS_MODELS.get(model_key, model_key)

    # ------------------------------------------------------------------
    # TTSProvider interface
    # ------------------------------------------------------------------

    @retry(max_attempts=3, base_delay=5.0, exceptions=(ReplicateError, ConnectionError))
    def synthesize(
        self,
        text: str,
        voice_config: VoiceConfig,
        output_path: Path,
    ) -> tuple[Path, float]:
        """Generate speech via Replicate and write to *output_path*.

        The ``voice_config.model`` field can override the default model key.
        ``voice_config.voice_id`` is used as a speaker/voice description
        depending on the model.
        """
        model_id = self._resolve_model(voice_config)

        self.logger.info(
            "Replicate TTS: model=%s, text_len=%d, output=%s",
            model_id,
            len(text),
            output_path,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        input_params = self._build_input(text, voice_config, model_id)

        output = self._client.run(model_id, input=input_params)

        audio_url = self._extract_audio_url(output)
        self._download_audio(audio_url, output_path)

        duration = _get_audio_duration(output_path)
        self.logger.info(
            "Replicate TTS complete: %s (%.1fs)", output_path.name, duration
        )
        return output_path, duration

    @retry(max_attempts=2, base_delay=2.0, exceptions=(ReplicateError, ConnectionError))
    def list_voices(self) -> list[dict[str, Any]]:
        """Return the list of available Replicate TTS models as voice entries.

        Each entry contains model metadata rather than traditional voice IDs,
        since Replicate models typically accept free-form voice descriptions.
        """
        voices: list[dict[str, Any]] = []
        for key, model_id in REPLICATE_TTS_MODELS.items():
            voices.append(
                {
                    "voice_id": key,
                    "name": key.replace("-", " ").title(),
                    "provider": "replicate",
                    "model_id": model_id,
                    "supports_cloning": key == "xtts-v2",
                }
            )
        self.logger.info("Replicate TTS: %d models available", len(voices))
        return voices

    # ------------------------------------------------------------------
    # Clone-and-speak (XTTS-v2)
    # ------------------------------------------------------------------

    @retry(max_attempts=3, base_delay=5.0, exceptions=(ReplicateError, ConnectionError))
    def clone_and_speak(
        self,
        text: str,
        reference_audio: Path,
        output_path: Path,
        language: str = "en",
    ) -> tuple[Path, float]:
        """Clone a voice from reference audio and speak text using XTTS-v2.

        This performs inference-time voice cloning: the reference audio is
        uploaded alongside the text, and the model produces speech that
        mimics the reference speaker.

        Args:
            text: The text to speak.
            reference_audio: Path to a reference audio file (WAV/MP3,
                ideally 6--30 seconds of clean speech).
            output_path: Where to write the generated audio.
            language: Language code (default ``"en"``).

        Returns:
            ``(audio_path, duration_seconds)`` tuple.
        """
        if not reference_audio.exists():
            raise FileNotFoundError(f"Reference audio not found: {reference_audio}")

        self.logger.info(
            "Replicate clone-and-speak: ref=%s, text_len=%d",
            reference_audio.name,
            len(text),
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        xtts_model = REPLICATE_TTS_MODELS["xtts-v2"]

        with open(reference_audio, "rb") as ref_fh:
            output = self._client.run(
                xtts_model,
                input={
                    "text": text,
                    "speaker_wav": ref_fh,
                    "language": language,
                },
            )

        audio_url = self._extract_audio_url(output)
        self._download_audio(audio_url, output_path)

        duration = _get_audio_duration(output_path)
        self.logger.info(
            "Replicate clone-and-speak complete: %s (%.1fs)",
            output_path.name,
            duration,
        )
        return output_path, duration

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_model(self, voice_config: VoiceConfig) -> str:
        """Determine the Replicate model ID from the voice config."""
        if voice_config.model and voice_config.model in REPLICATE_TTS_MODELS:
            return REPLICATE_TTS_MODELS[voice_config.model]
        if voice_config.model:
            # Treat as a raw Replicate model identifier.
            return voice_config.model
        return self._model_id

    def _build_input(
        self, text: str, voice_config: VoiceConfig, model_id: str
    ) -> dict[str, Any]:
        """Build model-specific input parameters."""
        # Common base.
        params: dict[str, Any] = {"text": text}

        if "parler-tts" in model_id:
            # Parler-TTS uses a text description of the desired voice.
            params["description"] = voice_config.voice_id or (
                "A calm, clear, and professional narrator voice."
            )
        elif "xtts-v2" in model_id:
            params["language"] = "en"
            if voice_config.speed and voice_config.speed != 1.0:
                params["speed"] = voice_config.speed
        elif "tortoise-tts" in model_id:
            params["voice"] = voice_config.voice_id or "random"
            params["preset"] = "fast"  # Options: ultra_fast, fast, standard, high_quality
        elif "speech-01-turbo" in model_id:
            params["language"] = "en"
            if voice_config.voice_id:
                params["voice_id"] = voice_config.voice_id

        return params

    @staticmethod
    def _extract_audio_url(output: Any) -> str:
        """Extract an audio URL from Replicate output (URL string or list)."""
        if isinstance(output, list) and len(output) > 0:
            url = str(output[0])
        else:
            url = str(output)

        if not url:
            raise RuntimeError("Replicate returned empty output for TTS.")
        return url

    def _download_audio(self, url: str, output_path: Path) -> None:
        """Download audio from a URL and save to disk."""
        with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as resp:
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)
