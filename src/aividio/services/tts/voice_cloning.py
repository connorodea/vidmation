"""Voice cloning service — clone voices from audio samples via ElevenLabs or Replicate."""

from __future__ import annotations

import logging
import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

from aividio.config.settings import get_settings
from aividio.utils.retry import retry

if TYPE_CHECKING:
    from aividio.config.settings import Settings

logger = logging.getLogger(__name__)


class VoiceCloner:
    """Clone voices using ElevenLabs or Replicate models.

    Supports instant voice cloning from one or more audio samples,
    managing cloned voices, and generating previews.
    """

    # Minimum and maximum sample durations (seconds) for quality cloning.
    MIN_SAMPLE_DURATION_SECS = 10
    MAX_SAMPLES_ELEVENLABS = 25

    # Default preview text when none is provided.
    DEFAULT_PREVIEW_TEXT = "Hello, this is a preview of your cloned voice."

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.logger = logging.getLogger(f"aividio.services.{self.__class__.__name__}")

    # ------------------------------------------------------------------
    # ElevenLabs client (lazy init)
    # ------------------------------------------------------------------

    def _get_elevenlabs_client(self) -> Any:
        """Return an authenticated ElevenLabs client, lazily initialised."""
        from elevenlabs import ElevenLabs

        api_key = self.settings.elevenlabs_api_key.get_secret_value()
        if not api_key:
            raise ValueError(
                "elevenlabs_api_key is not configured. "
                "Set AIVIDIO_ELEVENLABS_API_KEY in your environment."
            )
        return ElevenLabs(api_key=api_key)

    # ------------------------------------------------------------------
    # Replicate client (lazy init)
    # ------------------------------------------------------------------

    def _get_replicate_client(self) -> Any:
        """Return an authenticated Replicate client, lazily initialised."""
        import replicate

        api_token = self.settings.replicate_api_token.get_secret_value()
        if not api_token:
            raise ValueError(
                "replicate_api_token is not configured. "
                "Set AIVIDIO_REPLICATE_API_TOKEN in your environment."
            )
        return replicate.Client(api_token=api_token)

    # ------------------------------------------------------------------
    # Clone
    # ------------------------------------------------------------------

    def clone_voice(
        self,
        audio_samples: list[Path],
        name: str,
        description: str = "",
        provider: str = "elevenlabs",
    ) -> dict[str, Any]:
        """Clone a voice from one or more audio samples.

        Args:
            audio_samples: Paths to audio files (WAV/MP3).  At least one is
                required; ElevenLabs supports up to 25 samples.
            name: Human-readable name for the cloned voice.
            description: Optional description for the voice.
            provider: Backend to use — ``"elevenlabs"`` (default) or
                ``"replicate"`` (XTTS-v2 based, stores reference locally).

        Returns:
            A dict containing ``voice_id``, ``name``, ``provider``, and
            ``preview_url`` (if available).

        Raises:
            ValueError: If no samples are provided or the provider is unknown.
            RuntimeError: If the provider API call fails.
        """
        if not audio_samples:
            raise ValueError("At least one audio sample is required for voice cloning.")

        # Validate all sample paths exist.
        for sample in audio_samples:
            if not sample.exists():
                raise FileNotFoundError(f"Audio sample not found: {sample}")

        self.logger.info(
            "Cloning voice %r with %d sample(s) via %s",
            name,
            len(audio_samples),
            provider,
        )

        if provider == "elevenlabs":
            return self._clone_elevenlabs(audio_samples, name, description)
        if provider == "replicate":
            return self._clone_replicate(audio_samples, name, description)

        raise ValueError(f"Unknown voice cloning provider: {provider!r}")

    @retry(max_attempts=2, base_delay=3.0, exceptions=(Exception,))
    def _clone_elevenlabs(
        self,
        audio_samples: list[Path],
        name: str,
        description: str,
    ) -> dict[str, Any]:
        """Clone a voice using ElevenLabs instant voice cloning API."""
        from elevenlabs.core import ApiError

        client = self._get_elevenlabs_client()

        if len(audio_samples) > self.MAX_SAMPLES_ELEVENLABS:
            self.logger.warning(
                "ElevenLabs supports up to %d samples; truncating from %d.",
                self.MAX_SAMPLES_ELEVENLABS,
                len(audio_samples),
            )
            audio_samples = audio_samples[: self.MAX_SAMPLES_ELEVENLABS]

        # Open all sample files for the API call.
        file_handles = []
        try:
            for sample_path in audio_samples:
                fh = open(sample_path, "rb")  # noqa: SIM115
                file_handles.append(fh)

            try:
                voice = client.clone(
                    name=name,
                    description=description or f"Cloned voice: {name}",
                    files=file_handles,
                )
            except ApiError as exc:
                self.logger.error("ElevenLabs clone API error: %s", exc)
                raise RuntimeError(f"ElevenLabs voice cloning failed: {exc}") from exc

        finally:
            for fh in file_handles:
                fh.close()

        result = {
            "voice_id": voice.voice_id,
            "name": voice.name,
            "provider": "elevenlabs",
            "preview_url": getattr(voice, "preview_url", None),
        }
        self.logger.info("Voice cloned successfully: %s", result)
        return result

    def _clone_replicate(
        self,
        audio_samples: list[Path],
        name: str,
        description: str,
    ) -> dict[str, Any]:
        """Register a voice for Replicate XTTS-v2 cloning.

        Replicate's XTTS-v2 model performs voice cloning at inference time
        using a reference audio sample.  We store the first sample path
        as the reference and generate a local voice ID.
        """
        # XTTS-v2 uses a single reference audio at inference time.
        reference_audio = audio_samples[0]

        voice_id = f"replicate_clone_{uuid.uuid4().hex[:12]}"
        result = {
            "voice_id": voice_id,
            "name": name,
            "provider": "replicate",
            "preview_url": None,
            "reference_audio": str(reference_audio),
            "description": description,
        }
        self.logger.info(
            "Replicate voice registered (inference-time cloning): %s", result
        )
        return result

    # ------------------------------------------------------------------
    # List cloned voices
    # ------------------------------------------------------------------

    def list_cloned_voices(self) -> list[dict[str, Any]]:
        """List all cloned voices across supported providers.

        Returns a combined list from ElevenLabs (filtering to cloned category)
        and any locally-registered Replicate voices.
        """
        voices: list[dict[str, Any]] = []

        # ElevenLabs cloned voices.
        try:
            voices.extend(self._list_elevenlabs_cloned())
        except Exception as exc:
            self.logger.warning("Could not fetch ElevenLabs cloned voices: %s", exc)

        return voices

    def _list_elevenlabs_cloned(self) -> list[dict[str, Any]]:
        """Fetch cloned voices from ElevenLabs."""
        client = self._get_elevenlabs_client()
        response = client.voices.get_all()

        cloned: list[dict[str, Any]] = []
        for voice in response.voices:
            category = getattr(voice, "category", "")
            if category in ("cloned", "professional"):
                cloned.append(
                    {
                        "voice_id": voice.voice_id,
                        "name": voice.name,
                        "provider": "elevenlabs",
                        "category": category,
                        "preview_url": getattr(voice, "preview_url", None),
                        "labels": getattr(voice, "labels", {}),
                    }
                )

        self.logger.info("Found %d cloned voices on ElevenLabs", len(cloned))
        return cloned

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_cloned_voice(
        self, voice_id: str, provider: str = "elevenlabs"
    ) -> bool:
        """Delete a cloned voice.

        Args:
            voice_id: The provider-specific voice ID.
            provider: ``"elevenlabs"`` or ``"replicate"``.

        Returns:
            ``True`` if the voice was deleted, ``False`` otherwise.
        """
        self.logger.info("Deleting voice %s from %s", voice_id, provider)

        if provider == "elevenlabs":
            return self._delete_elevenlabs_voice(voice_id)
        if provider == "replicate":
            # Replicate cloned voices are local references; nothing to delete
            # on the remote side.  The caller should remove the DB record.
            self.logger.info("Replicate voice %s removed (local only).", voice_id)
            return True

        self.logger.warning("Unknown provider %r for delete operation.", provider)
        return False

    @retry(max_attempts=2, base_delay=2.0, exceptions=(Exception,))
    def _delete_elevenlabs_voice(self, voice_id: str) -> bool:
        """Delete a voice from ElevenLabs."""
        from elevenlabs.core import ApiError

        client = self._get_elevenlabs_client()
        try:
            client.voices.delete(voice_id=voice_id)
            self.logger.info("ElevenLabs voice %s deleted.", voice_id)
            return True
        except ApiError as exc:
            self.logger.error("Failed to delete ElevenLabs voice %s: %s", voice_id, exc)
            return False

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def preview_voice(
        self,
        voice_id: str,
        text: str | None = None,
        provider: str = "elevenlabs",
        output_dir: Path | None = None,
    ) -> Path:
        """Generate a short audio preview with a cloned voice.

        Args:
            voice_id: The voice to preview.
            text: Optional custom text; defaults to a standard greeting.
            provider: ``"elevenlabs"`` or ``"replicate"``.
            output_dir: Directory for the preview file.  Uses a temp dir if
                *None*.

        Returns:
            Path to the generated preview audio file.
        """
        text = text or self.DEFAULT_PREVIEW_TEXT

        if output_dir is None:
            output_dir = Path(tempfile.gettempdir()) / "aividio" / "voice_previews"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"preview_{voice_id[:20]}_{uuid.uuid4().hex[:8]}.mp3"

        self.logger.info(
            "Generating preview for voice %s via %s", voice_id, provider
        )

        if provider == "elevenlabs":
            return self._preview_elevenlabs(voice_id, text, output_path)
        if provider == "replicate":
            return self._preview_replicate(voice_id, text, output_path)

        raise ValueError(f"Unknown provider for preview: {provider!r}")

    @retry(max_attempts=2, base_delay=2.0, exceptions=(Exception,))
    def _preview_elevenlabs(
        self, voice_id: str, text: str, output_path: Path
    ) -> Path:
        """Generate a preview via ElevenLabs TTS."""
        client = self._get_elevenlabs_client()
        audio_iterator = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id="eleven_multilingual_v2",
            voice_settings={
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        )

        with open(output_path, "wb") as f:
            for chunk in audio_iterator:
                f.write(chunk)

        self.logger.info("ElevenLabs preview saved: %s", output_path)
        return output_path

    @retry(max_attempts=2, base_delay=5.0, exceptions=(Exception,))
    def _preview_replicate(
        self, voice_id: str, text: str, output_path: Path
    ) -> Path:
        """Generate a preview via Replicate XTTS-v2.

        Note: For Replicate-based cloned voices the ``voice_id`` encodes
        a local reference; the caller must supply the reference audio
        separately for true cloning.  This method generates a preview using
        the default XTTS-v2 voice.
        """
        client = self._get_replicate_client()

        output = client.run(
            "lucataco/xtts-v2:684bc3855b37866c0c65add2ff39c78f3dea3f4ff103a436465326e0f438d55e",
            input={
                "text": text,
                "language": "en",
            },
        )

        # Replicate returns a URL to the generated audio.
        audio_url = str(output) if not isinstance(output, list) else str(output[0])

        with httpx.stream("GET", audio_url, timeout=120.0, follow_redirects=True) as resp:
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)

        self.logger.info("Replicate preview saved: %s", output_path)
        return output_path
