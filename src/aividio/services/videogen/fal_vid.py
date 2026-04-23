"""fal.ai video generator — text-to-video and image-to-video via fal.ai API."""

from __future__ import annotations

import base64
import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

import fal_client
import httpx

from aividio.services.videogen.base import VideoGenerator
from aividio.utils.retry import retry

if TYPE_CHECKING:
    from aividio.config.settings import Settings

# ---------------------------------------------------------------------------
# Supported models
# ---------------------------------------------------------------------------

MODELS: dict[str, dict[str, Any]] = {
    "fal-ai/kling-video/v2.1/master": {
        "name": "Kling Video 2.1 Master",
        "supports_i2v": True,
        "max_duration": 10.0,
        "cost_per_second": 0.06,
        "default_params": {},
    },
    "fal-ai/minimax/video-01-live": {
        "name": "MiniMax Video-01-Live (fal)",
        "supports_i2v": True,
        "max_duration": 6.0,
        "cost_per_second": 0.035,
        "default_params": {},
    },
    "fal-ai/hunyuan-video": {
        "name": "Hunyuan Video (fal)",
        "supports_i2v": False,
        "max_duration": 5.0,
        "cost_per_second": 0.02,
        "default_params": {},
    },
    "fal-ai/runway-gen3/turbo": {
        "name": "Runway Gen-3 Turbo (fal)",
        "supports_i2v": True,
        "max_duration": 10.0,
        "cost_per_second": 0.07,
        "default_params": {},
    },
}

DEFAULT_MODEL = "fal-ai/kling-video/v2.1/master"

# Aspect-ratio to pixel dimension mapping.
ASPECT_RATIO_MAP: dict[str, tuple[int, int]] = {
    "16:9": (1280, 720),
    "9:16": (720, 1280),
    "1:1": (720, 720),
    "4:3": (960, 720),
    "3:4": (720, 960),
}


class FalVideoGenerator(VideoGenerator):
    """Generate video clips via the fal.ai API.

    Supports multiple models, text-to-video and image-to-video through
    ``fal_client.subscribe()`` for queued execution with automatic polling.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        model_id: str = DEFAULT_MODEL,
    ) -> None:
        super().__init__(settings=settings)
        fal_key = self.settings.fal_key.get_secret_value()
        if not fal_key:
            raise ValueError(
                "fal_key is not configured. "
                "Set AIVIDIO_FAL_KEY in your environment."
            )
        # fal_client reads FAL_KEY from the environment.
        import os

        os.environ["FAL_KEY"] = fal_key
        self._model_id = model_id

        if self._model_id not in MODELS:
            self.logger.warning(
                "Model %r not in known registry — using it as a custom endpoint",
                self._model_id,
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_output_path(self, output_path: Path | None, prefix: str) -> Path:
        """Determine final output path, creating parent directories as needed."""
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            return output_path

        output_dir = Path(tempfile.gettempdir()) / "aividio" / "videogen"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / f"fal_{prefix}_{uuid.uuid4().hex[:12]}.mp4"

    def _download_video(self, url: str, output_path: Path) -> Path:
        """Download a video from *url* to *output_path*."""
        self.logger.info("Downloading video to %s ...", output_path)
        with httpx.stream(
            "GET", url, timeout=300.0, follow_redirects=True
        ) as resp:
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=16384):
                    f.write(chunk)
        self.logger.info(
            "Video saved: %s (%.2f MB)",
            output_path,
            output_path.stat().st_size / 1e6,
        )
        return output_path

    def _extract_video_url(self, result: dict[str, Any]) -> str:
        """Extract the video URL from a fal.ai result payload."""
        # Most video models return {"video": {"url": ...}} or {"output": {"url": ...}}
        if "video" in result:
            video = result["video"]
            if isinstance(video, dict) and "url" in video:
                return video["url"]
            if isinstance(video, str):
                return video

        if "output" in result:
            output = result["output"]
            if isinstance(output, dict) and "url" in output:
                return output["url"]
            if isinstance(output, str):
                return output

        # Some models return a list of videos
        if "videos" in result and result["videos"]:
            first = result["videos"][0]
            if isinstance(first, dict) and "url" in first:
                return first["url"]
            return str(first)

        # Fallback: check for a top-level "url" key
        if "url" in result:
            return result["url"]

        raise RuntimeError(
            f"Could not extract video URL from fal.ai result: {list(result.keys())}"
        )

    def _on_queue_update(self, update: Any) -> None:
        """Callback for fal_client.subscribe queue updates."""
        if hasattr(update, "logs"):
            for log in update.logs:
                self.logger.info("[fal queue] %s", log.get("message", log) if isinstance(log, dict) else log)

    def _build_t2v_arguments(
        self, prompt: str, duration: float, aspect_ratio: str
    ) -> dict[str, Any]:
        """Build the arguments dict for a text-to-video call."""
        width, height = ASPECT_RATIO_MAP.get(aspect_ratio, (1280, 720))
        model_meta = MODELS.get(self._model_id, {})
        args: dict[str, Any] = {
            "prompt": prompt,
            **model_meta.get("default_params", {}),
        }

        if "kling" in self._model_id:
            args["duration"] = str(min(duration, 10.0))
            args["aspect_ratio"] = aspect_ratio
        elif "minimax" in self._model_id:
            args["prompt_optimizer"] = True
        elif "hunyuan" in self._model_id:
            args["width"] = width
            args["height"] = height
        elif "runway" in self._model_id:
            args["duration"] = int(min(duration, 10))
            args["ratio"] = aspect_ratio

        return args

    def _build_i2v_arguments(
        self, image_path: Path, prompt: str, duration: float
    ) -> dict[str, Any]:
        """Build the arguments dict for an image-to-video call."""
        # Encode image as data URI
        image_bytes = image_path.read_bytes()
        mime = "image/png" if image_path.suffix == ".png" else "image/jpeg"
        data_uri = f"data:{mime};base64,{base64.b64encode(image_bytes).decode()}"

        model_meta = MODELS.get(self._model_id, {})
        args: dict[str, Any] = {
            "prompt": prompt,
            "image_url": data_uri,
            **model_meta.get("default_params", {}),
        }

        if "kling" in self._model_id:
            args["duration"] = str(min(duration, 10.0))
        elif "minimax" in self._model_id:
            args["first_frame_image"] = data_uri
            args.pop("image_url", None)
            args["prompt_optimizer"] = True
        elif "runway" in self._model_id:
            args["image"] = data_uri
            args.pop("image_url", None)
            args["duration"] = int(min(duration, 10))

        return args

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @retry(max_attempts=2, base_delay=10.0, exceptions=(Exception,))
    def generate(
        self,
        prompt: str,
        duration: float = 5.0,
        aspect_ratio: str = "16:9",
        output_path: Path | None = None,
    ) -> Path:
        """Generate a video clip from a text prompt via fal.ai."""
        self.logger.info(
            "fal.ai T2V: model=%s, prompt=%r, duration=%.1fs, ratio=%s",
            self._model_id,
            prompt[:80],
            duration,
            aspect_ratio,
        )

        arguments = self._build_t2v_arguments(prompt, duration, aspect_ratio)

        result: dict[str, Any] = fal_client.subscribe(
            self._model_id,
            arguments=arguments,
            with_logs=True,
            on_queue_update=self._on_queue_update,
        )

        video_url = self._extract_video_url(result)
        dest = self._resolve_output_path(output_path, "t2v")
        return self._download_video(video_url, dest)

    @retry(max_attempts=2, base_delay=10.0, exceptions=(Exception,))
    def generate_from_image(
        self,
        image_path: Path,
        prompt: str,
        duration: float = 5.0,
        output_path: Path | None = None,
    ) -> Path:
        """Generate a video clip from a reference image via fal.ai."""
        model_meta = MODELS.get(self._model_id, {})
        if not model_meta.get("supports_i2v", False):
            raise ValueError(
                f"Model {self._model_id!r} does not support image-to-video. "
                f"Use one of: {[m for m, v in MODELS.items() if v.get('supports_i2v')]}"
            )

        if not image_path.exists():
            raise FileNotFoundError(f"Source image not found: {image_path}")

        self.logger.info(
            "fal.ai I2V: model=%s, image=%s, prompt=%r",
            self._model_id,
            image_path.name,
            prompt[:80],
        )

        arguments = self._build_i2v_arguments(image_path, prompt, duration)

        result: dict[str, Any] = fal_client.subscribe(
            self._model_id,
            arguments=arguments,
            with_logs=True,
            on_queue_update=self._on_queue_update,
        )

        video_url = self._extract_video_url(result)
        dest = self._resolve_output_path(output_path, "i2v")
        return self._download_video(video_url, dest)

    def list_models(self) -> list[dict]:
        """Return metadata for all supported fal.ai video models."""
        return [
            {
                "id": model_id,
                "name": meta["name"],
                "supports_i2v": meta["supports_i2v"],
                "max_duration": meta["max_duration"],
                "cost_per_second": meta["cost_per_second"],
                "provider": "fal",
            }
            for model_id, meta in MODELS.items()
        ]

    def estimate_cost(self, duration: float, model: str | None = None) -> float:
        """Estimate USD cost for a video clip of the given duration."""
        model = model or self._model_id
        meta = MODELS.get(model)
        if meta is None:
            self.logger.warning(
                "No cost data for model %r, estimating at $0.05/s", model
            )
            return duration * 0.05
        return duration * meta["cost_per_second"]
