"""Replicate video generator — text-to-video and image-to-video via Replicate API."""

from __future__ import annotations

import base64
import tempfile
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import replicate
from replicate.exceptions import ReplicateError

from vidmation.services.videogen.base import VideoGenerator
from vidmation.utils.retry import retry

if TYPE_CHECKING:
    from vidmation.config.settings import Settings

# ---------------------------------------------------------------------------
# Supported models
# ---------------------------------------------------------------------------

MODELS: dict[str, dict[str, Any]] = {
    "minimax/video-01-live": {
        "name": "MiniMax Video-01-Live",
        "supports_i2v": True,
        "max_duration": 6.0,
        "cost_per_second": 0.035,
        "default_params": {},
    },
    "luma/ray": {
        "name": "Luma Dream Machine (Ray)",
        "supports_i2v": True,
        "max_duration": 5.0,
        "cost_per_second": 0.05,
        "default_params": {},
    },
    "tencent/hunyuan-video": {
        "name": "Tencent Hunyuan Video",
        "supports_i2v": False,
        "max_duration": 5.0,
        "cost_per_second": 0.02,
        "default_params": {},
    },
    "wan-ai/wan2.1-t2v-14b": {
        "name": "Wan AI 2.1 T2V 14B",
        "supports_i2v": False,
        "max_duration": 5.0,
        "cost_per_second": 0.015,
        "default_params": {},
    },
}

DEFAULT_MODEL = "minimax/video-01-live"

# Aspect-ratio to pixel dimension mapping for models that need explicit sizes.
ASPECT_RATIO_MAP: dict[str, tuple[int, int]] = {
    "16:9": (1280, 720),
    "9:16": (720, 1280),
    "1:1": (720, 720),
    "4:3": (960, 720),
    "3:4": (720, 960),
}


class ReplicateVideoGenerator(VideoGenerator):
    """Generate video clips via the Replicate API.

    Supports multiple models, text-to-video and image-to-video.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        model_id: str = DEFAULT_MODEL,
    ) -> None:
        super().__init__(settings=settings)
        api_token = self.settings.replicate_api_token.get_secret_value()
        if not api_token:
            raise ValueError(
                "replicate_api_token is not configured. "
                "Set VIDMATION_REPLICATE_API_TOKEN in your environment."
            )
        self._client = replicate.Client(api_token=api_token)
        self._model_id = model_id

        if self._model_id not in MODELS:
            self.logger.warning(
                "Model %r not in known registry — using it as a custom model ID",
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

        output_dir = Path(tempfile.gettempdir()) / "vidmation" / "videogen"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / f"replicate_{prefix}_{uuid.uuid4().hex[:12]}.mp4"

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
        self.logger.info("Video saved: %s (%.2f MB)", output_path, output_path.stat().st_size / 1e6)
        return output_path

    def _extract_video_url(self, output: Any) -> str:
        """Extract the video URL from Replicate prediction output."""
        if isinstance(output, str):
            return output
        if isinstance(output, list) and len(output) > 0:
            return str(output[0])
        # FileOutput or similar
        url = str(output)
        if not url or url == "None":
            raise RuntimeError("Replicate returned empty output for video generation")
        return url

    def _build_t2v_input(
        self, prompt: str, duration: float, aspect_ratio: str
    ) -> dict[str, Any]:
        """Build the input dict for a text-to-video prediction."""
        width, height = ASPECT_RATIO_MAP.get(aspect_ratio, (1280, 720))
        model_meta = MODELS.get(self._model_id, {})
        params: dict[str, Any] = {
            "prompt": prompt,
            **model_meta.get("default_params", {}),
        }

        # Model-specific parameter names
        if "minimax" in self._model_id:
            params["prompt_optimizer"] = True
        elif "luma" in self._model_id:
            params["aspect_ratio"] = aspect_ratio
        elif "hunyuan" in self._model_id:
            params["width"] = width
            params["height"] = height
        elif "wan" in self._model_id:
            params["width"] = width
            params["height"] = height

        return params

    def _build_i2v_input(
        self, image_path: Path, prompt: str, duration: float
    ) -> dict[str, Any]:
        """Build the input dict for an image-to-video prediction."""
        # Encode image as data URI for Replicate
        image_bytes = image_path.read_bytes()
        mime = "image/png" if image_path.suffix == ".png" else "image/jpeg"
        data_uri = f"data:{mime};base64,{base64.b64encode(image_bytes).decode()}"

        model_meta = MODELS.get(self._model_id, {})
        params: dict[str, Any] = {
            "prompt": prompt,
            "image": data_uri,
            **model_meta.get("default_params", {}),
        }

        if "minimax" in self._model_id:
            params["first_frame_image"] = data_uri
            params.pop("image", None)
            params["prompt_optimizer"] = True
        elif "luma" in self._model_id:
            params["start_image"] = data_uri
            params.pop("image", None)

        return params

    def _run_prediction(self, input_params: dict[str, Any]) -> str:
        """Submit a prediction and poll until completion, returning the video URL."""
        self.logger.info(
            "Starting Replicate prediction: model=%s", self._model_id
        )

        prediction = self._client.predictions.create(
            model=self._model_id,
            input=input_params,
        )

        # Poll for completion
        poll_interval = 5.0
        max_wait = 600  # 10 minutes
        elapsed = 0.0

        while prediction.status not in ("succeeded", "failed", "canceled"):
            time.sleep(poll_interval)
            elapsed += poll_interval
            prediction.reload()

            self.logger.info(
                "Prediction %s: status=%s (%.0fs elapsed)",
                prediction.id,
                prediction.status,
                elapsed,
            )

            if elapsed >= max_wait:
                raise TimeoutError(
                    f"Replicate prediction {prediction.id} timed out after {max_wait}s"
                )

            # Adaptive polling — slow down after initial burst
            if elapsed > 30:
                poll_interval = 10.0

        if prediction.status != "succeeded":
            error_msg = getattr(prediction, "error", "Unknown error")
            raise RuntimeError(
                f"Replicate prediction {prediction.id} {prediction.status}: {error_msg}"
            )

        return self._extract_video_url(prediction.output)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @retry(max_attempts=2, base_delay=10.0, exceptions=(ReplicateError, ConnectionError))
    def generate(
        self,
        prompt: str,
        duration: float = 5.0,
        aspect_ratio: str = "16:9",
        output_path: Path | None = None,
    ) -> Path:
        """Generate a video clip from a text prompt via Replicate."""
        self.logger.info(
            "Replicate T2V: model=%s, prompt=%r, duration=%.1fs, ratio=%s",
            self._model_id,
            prompt[:80],
            duration,
            aspect_ratio,
        )

        input_params = self._build_t2v_input(prompt, duration, aspect_ratio)
        video_url = self._run_prediction(input_params)

        dest = self._resolve_output_path(output_path, "t2v")
        return self._download_video(video_url, dest)

    @retry(max_attempts=2, base_delay=10.0, exceptions=(ReplicateError, ConnectionError))
    def generate_from_image(
        self,
        image_path: Path,
        prompt: str,
        duration: float = 5.0,
        output_path: Path | None = None,
    ) -> Path:
        """Generate a video clip from a reference image via Replicate."""
        model_meta = MODELS.get(self._model_id, {})
        if not model_meta.get("supports_i2v", False):
            raise ValueError(
                f"Model {self._model_id!r} does not support image-to-video. "
                f"Use one of: {[m for m, v in MODELS.items() if v.get('supports_i2v')]}"
            )

        if not image_path.exists():
            raise FileNotFoundError(f"Source image not found: {image_path}")

        self.logger.info(
            "Replicate I2V: model=%s, image=%s, prompt=%r",
            self._model_id,
            image_path.name,
            prompt[:80],
        )

        input_params = self._build_i2v_input(image_path, prompt, duration)
        video_url = self._run_prediction(input_params)

        dest = self._resolve_output_path(output_path, "i2v")
        return self._download_video(video_url, dest)

    def list_models(self) -> list[dict]:
        """Return metadata for all supported Replicate video models."""
        return [
            {
                "id": model_id,
                "name": meta["name"],
                "supports_i2v": meta["supports_i2v"],
                "max_duration": meta["max_duration"],
                "cost_per_second": meta["cost_per_second"],
                "provider": "replicate",
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
