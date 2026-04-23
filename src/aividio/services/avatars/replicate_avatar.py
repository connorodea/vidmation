"""Replicate-hosted AI avatar (talking-head) provider."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import replicate
from replicate.exceptions import ReplicateError

from aividio.config.profiles import VoiceConfig
from aividio.services.avatars.base import AvatarProvider
from aividio.utils.retry import retry

if TYPE_CHECKING:
    from aividio.config.settings import Settings


# Replicate model identifiers for avatar generation.
REPLICATE_AVATAR_MODELS: dict[str, str] = {
    "sadtalker": "cjwbw/sadtalker:a519cc0cfebaaeade068b23899165a11ec76aaa1a2de25ea4e7695d22ceed797",
    "liveportrait": "lucataco/liveportrait:067dd98cc29e09643c73ca7df21c6913e1e53a32869b4ca4fbea046b81b1e35a",
}

DEFAULT_MODEL_KEY = "sadtalker"

# Built-in avatar presets (reference images bundled with the project).
BUILTIN_AVATARS: list[dict[str, str]] = [
    {
        "avatar_id": "presenter_male_01",
        "name": "Professional Male Presenter",
        "description": "Front-facing male presenter, neutral background.",
        "type": "builtin",
    },
    {
        "avatar_id": "presenter_female_01",
        "name": "Professional Female Presenter",
        "description": "Front-facing female presenter, neutral background.",
        "type": "builtin",
    },
    {
        "avatar_id": "narrator_neutral",
        "name": "Neutral Narrator",
        "description": "Gender-neutral narrator with clean background.",
        "type": "builtin",
    },
]


class ReplicateAvatarProvider(AvatarProvider):
    """Generate talking-head avatar videos via Replicate.

    Supports:
        - **SadTalker** (``cjwbw/sadtalker``) -- Single image + audio to
          talking head.  Good for still reference images.
        - **LivePortrait** (``lucataco/liveportrait``) -- Video-driven
          animation.  Best with video reference + driving audio.

    Workflow:
        1. Generate TTS audio (or accept pre-generated audio).
        2. Send reference image/video + audio to the avatar model.
        3. Download and save the resulting video.
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
                "Set AIVIDIO_REPLICATE_API_TOKEN in your environment."
            )
        self._client = replicate.Client(api_token=api_token)
        self._model_key = model_key
        self._model_id = REPLICATE_AVATAR_MODELS.get(model_key, model_key)

    # ------------------------------------------------------------------
    # AvatarProvider interface
    # ------------------------------------------------------------------

    @retry(max_attempts=3, base_delay=10.0, exceptions=(ReplicateError, ConnectionError))
    def generate(
        self,
        text: str,
        avatar_id: str,
        voice_config: VoiceConfig,
        output_path: Path,
        *,
        audio_path: Path | None = None,
    ) -> Path:
        """Generate an avatar video speaking the given text.

        If *audio_path* is not provided, TTS is performed first using
        the configured voice settings.
        """
        self.logger.info(
            "Replicate avatar: model=%s, avatar=%s, text_len=%d",
            self._model_id,
            avatar_id,
            len(text),
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Step 1: Ensure we have audio.
        if audio_path is None:
            audio_path = self._generate_audio(text, voice_config)
        elif not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Step 2: Resolve the avatar reference image/video.
        avatar_ref_path = self._resolve_avatar_path(avatar_id)

        # Step 3: Run the avatar model.
        input_params = self._build_input(avatar_ref_path, audio_path)

        output = self._client.run(self._model_id, input=input_params)

        video_url = self._extract_video_url(output)
        self._download_file(video_url, output_path)

        self.logger.info("Replicate avatar video saved: %s", output_path)
        return output_path

    def list_avatars(self) -> list[dict[str, Any]]:
        """Return available avatar presets (built-in + custom)."""
        avatars: list[dict[str, Any]] = []
        for preset in BUILTIN_AVATARS:
            avatars.append(
                {
                    **preset,
                    "provider": "replicate",
                    "preview_url": None,
                }
            )
        self.logger.info("Replicate avatars: %d available", len(avatars))
        return avatars

    def create_avatar(
        self,
        video_sample: Path,
        name: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Create a custom avatar from a video or image sample.

        The sample is stored locally and registered as a custom avatar.
        For Replicate-based models the reference is used at inference time;
        no training step is required.
        """
        if not video_sample.exists():
            raise FileNotFoundError(f"Video sample not found: {video_sample}")

        # Store the sample in the data directory.
        avatar_id = f"custom_{uuid.uuid4().hex[:12]}"
        avatars_dir = self.settings.data_dir / "avatars" / avatar_id
        avatars_dir.mkdir(parents=True, exist_ok=True)

        # Copy the sample to the avatars directory.
        dest_path = avatars_dir / video_sample.name
        dest_path.write_bytes(video_sample.read_bytes())

        result = {
            "avatar_id": avatar_id,
            "name": name,
            "description": description,
            "provider": "replicate",
            "reference_path": str(dest_path),
            "preview_url": None,
        }
        self.logger.info("Custom avatar created: %s", result)
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _generate_audio(self, text: str, voice_config: VoiceConfig) -> Path:
        """Generate TTS audio for the avatar.

        Uses the configured TTS provider from the voice config.
        """
        from aividio.services.tts import create_tts_provider

        tts = create_tts_provider(
            provider=voice_config.provider, settings=self.settings
        )

        audio_dir = Path(tempfile.gettempdir()) / "aividio" / "avatar_audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_path = audio_dir / f"avatar_tts_{uuid.uuid4().hex[:12]}.mp3"

        path, duration = tts.synthesize(text, voice_config, audio_path)
        self.logger.info("Avatar TTS audio generated: %s (%.1fs)", path, duration)
        return path

    def _resolve_avatar_path(self, avatar_id: str) -> Path:
        """Resolve an avatar ID to a local image/video file path.

        Checks for custom avatars in the data directory first, then falls
        back to built-in assets.
        """
        # Check custom avatars.
        custom_dir = self.settings.data_dir / "avatars" / avatar_id
        if custom_dir.exists():
            # Use the first file in the directory.
            files = sorted(custom_dir.iterdir())
            if files:
                return files[0]

        # Check built-in avatar assets.
        builtin_dir = self.settings.assets_dir / "avatars"
        for ext in (".png", ".jpg", ".jpeg", ".mp4", ".webm"):
            candidate = builtin_dir / f"{avatar_id}{ext}"
            if candidate.exists():
                return candidate

        raise FileNotFoundError(
            f"Avatar reference not found for avatar_id={avatar_id!r}. "
            f"Checked: {custom_dir}, {builtin_dir}"
        )

    def _build_input(
        self, avatar_ref_path: Path, audio_path: Path
    ) -> dict[str, Any]:
        """Build model-specific input parameters."""
        if "sadtalker" in self._model_id:
            return {
                "source_image": open(avatar_ref_path, "rb"),  # noqa: SIM115
                "driven_audio": open(audio_path, "rb"),  # noqa: SIM115
                "still": True,  # Reduce head motion.
                "preprocess": "crop",
                "enhancer": "gfpgan",
            }

        if "liveportrait" in self._model_id:
            return {
                "image": open(avatar_ref_path, "rb"),  # noqa: SIM115
                "audio": open(audio_path, "rb"),  # noqa: SIM115
            }

        # Generic fallback.
        return {
            "image": open(avatar_ref_path, "rb"),  # noqa: SIM115
            "audio": open(audio_path, "rb"),  # noqa: SIM115
        }

    @staticmethod
    def _extract_video_url(output: Any) -> str:
        """Extract the video URL from Replicate output."""
        if isinstance(output, list) and len(output) > 0:
            url = str(output[0])
        else:
            url = str(output)

        if not url:
            raise RuntimeError("Replicate returned empty output for avatar generation.")
        return url

    def _download_file(self, url: str, output_path: Path) -> None:
        """Download a file from a URL and save to disk."""
        with httpx.stream("GET", url, timeout=300.0, follow_redirects=True) as resp:
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)
