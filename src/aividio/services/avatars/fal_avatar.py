"""fal.ai-hosted AI avatar (talking-head) provider."""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

import fal_client
import httpx

from aividio.config.profiles import VoiceConfig
from aividio.services.avatars.base import AvatarProvider
from aividio.utils.retry import retry

if TYPE_CHECKING:
    from aividio.config.settings import Settings


# Supported fal.ai avatar model endpoints.
FAL_AVATAR_MODELS: dict[str, str] = {
    "sadtalker": "fal-ai/sadtalker",
    "liveportrait": "fal-ai/liveportrait",
}

DEFAULT_MODEL_KEY = "sadtalker"

# Built-in avatar presets.
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


class FalAvatarProvider(AvatarProvider):
    """Generate talking-head avatar videos via fal.ai.

    Supports:
        - **SadTalker** (``fal-ai/sadtalker``) -- Single image + audio to
          talking head.
        - **LivePortrait** (``fal-ai/liveportrait``) -- Video-driven animation
          with driving audio.

    Workflow:
        1. Generate TTS audio (or accept pre-generated audio).
        2. Upload reference image and audio to fal.ai.
        3. Run the lip-sync model.
        4. Download the resulting video.
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
        os.environ["FAL_KEY"] = fal_key

        self._model_key = model_key
        self._model_id = FAL_AVATAR_MODELS.get(model_key, model_key)

    # ------------------------------------------------------------------
    # AvatarProvider interface
    # ------------------------------------------------------------------

    @retry(max_attempts=3, base_delay=10.0, exceptions=(Exception,))
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

        If *audio_path* is not provided, TTS is performed first.
        """
        self.logger.info(
            "fal.ai avatar: model=%s, avatar=%s, text_len=%d",
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

        # Step 2: Resolve the avatar reference.
        avatar_ref_path = self._resolve_avatar_path(avatar_id)

        # Step 3: Upload files to fal.ai.
        source_url = fal_client.upload_file(str(avatar_ref_path))
        audio_url = fal_client.upload_file(str(audio_path))

        # Step 4: Run the avatar model.
        input_args = self._build_input(source_url, audio_url)
        result: dict[str, Any] = fal_client.subscribe(
            self._model_id,
            arguments=input_args,
        )

        # Step 5: Download result.
        video_url = self._extract_video_url(result)
        self._download_file(video_url, output_path)

        self.logger.info("fal.ai avatar video saved: %s", output_path)
        return output_path

    def list_avatars(self) -> list[dict[str, Any]]:
        """Return available avatar presets."""
        avatars: list[dict[str, Any]] = []
        for preset in BUILTIN_AVATARS:
            avatars.append(
                {
                    **preset,
                    "provider": "fal",
                    "preview_url": None,
                }
            )
        self.logger.info("fal.ai avatars: %d available", len(avatars))
        return avatars

    def create_avatar(
        self,
        video_sample: Path,
        name: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Create a custom avatar from a video or image sample.

        The sample is stored locally.  fal.ai models use the reference
        at inference time -- no training is needed.
        """
        if not video_sample.exists():
            raise FileNotFoundError(f"Video sample not found: {video_sample}")

        avatar_id = f"custom_{uuid.uuid4().hex[:12]}"
        avatars_dir = self.settings.data_dir / "avatars" / avatar_id
        avatars_dir.mkdir(parents=True, exist_ok=True)

        dest_path = avatars_dir / video_sample.name
        dest_path.write_bytes(video_sample.read_bytes())

        result = {
            "avatar_id": avatar_id,
            "name": name,
            "description": description,
            "provider": "fal",
            "reference_path": str(dest_path),
            "preview_url": None,
        }
        self.logger.info("Custom avatar created: %s", result)
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _generate_audio(self, text: str, voice_config: VoiceConfig) -> Path:
        """Generate TTS audio for the avatar."""
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
        """Resolve an avatar ID to a local image/video file path."""
        # Custom avatars.
        custom_dir = self.settings.data_dir / "avatars" / avatar_id
        if custom_dir.exists():
            files = sorted(custom_dir.iterdir())
            if files:
                return files[0]

        # Built-in assets.
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
        self, source_url: str, audio_url: str
    ) -> dict[str, Any]:
        """Build model-specific input arguments."""
        if "sadtalker" in self._model_id:
            return {
                "source_image_url": source_url,
                "driven_audio_url": audio_url,
                "still": True,
                "preprocess": "crop",
                "enhancer": "gfpgan",
            }

        if "liveportrait" in self._model_id:
            return {
                "image_url": source_url,
                "audio_url": audio_url,
            }

        # Generic fallback.
        return {
            "source_url": source_url,
            "audio_url": audio_url,
        }

    @staticmethod
    def _extract_video_url(result: dict[str, Any]) -> str:
        """Extract the video URL from a fal.ai result payload."""
        video_data = result.get("video") or result.get("video_url") or {}
        if isinstance(video_data, dict):
            url = video_data.get("url", "")
        elif isinstance(video_data, str):
            url = video_data
        else:
            url = ""

        if not url:
            url = result.get("url", "")

        if not url:
            raise RuntimeError(
                f"fal.ai avatar returned no video URL. Keys: {list(result.keys())}"
            )
        return url

    def _download_file(self, url: str, output_path: Path) -> None:
        """Download a file from a URL and save to disk."""
        with httpx.stream("GET", url, timeout=300.0, follow_redirects=True) as resp:
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)
