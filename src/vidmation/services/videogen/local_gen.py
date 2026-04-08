"""Local video generator — procedural clip generation using FFmpeg.

Produces short video clips entirely on the local machine without any external
API calls.  Useful as a free fallback for text cards, Ken Burns on images,
gradient backgrounds, and simple motion graphics.

Requires ``ffmpeg-python`` (``pip install ffmpeg-python``) and ``ffmpeg`` on PATH.
"""

from __future__ import annotations

import random
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

import ffmpeg

from vidmation.services.videogen.base import VideoGenerator

if TYPE_CHECKING:
    from vidmation.config.settings import Settings

# Aspect-ratio to pixel dimension mapping.
ASPECT_RATIO_MAP: dict[str, tuple[int, int]] = {
    "16:9": (1280, 720),
    "9:16": (720, 1280),
    "1:1": (720, 720),
    "4:3": (960, 720),
    "3:4": (720, 960),
}


def _ensure_ffmpeg() -> str:
    """Return the path to ffmpeg, raising if it's missing."""
    path = shutil.which("ffmpeg")
    if path is None:
        raise EnvironmentError(
            "ffmpeg is not installed or not on PATH. "
            "Install it with: brew install ffmpeg  (macOS) or apt install ffmpeg (Linux)"
        )
    return path


class LocalVideoGenerator(VideoGenerator):
    """Procedural video generation using FFmpeg — no external API required.

    Supported generation modes (selected via prompt keywords or explicit type):

    * **ken_burns** — Pan and zoom on a source image.
    * **text_card** — Animated text on a solid or gradient background.
    * **gradient** — Slowly animating colour gradient.
    * **particles** — Simple particle / sparkle overlay.
    * **waveform** — Audio-reactive waveform visualisation.
    """

    # Available "models" (generation modes)
    MODES: dict[str, dict[str, Any]] = {
        "ken_burns": {
            "name": "Ken Burns (zoom/pan on image)",
            "supports_i2v": True,
            "max_duration": 60.0,
        },
        "text_card": {
            "name": "Animated Text Card",
            "supports_i2v": False,
            "max_duration": 30.0,
        },
        "gradient": {
            "name": "Gradient Background Animation",
            "supports_i2v": False,
            "max_duration": 60.0,
        },
        "particles": {
            "name": "Particle Effect Overlay",
            "supports_i2v": False,
            "max_duration": 30.0,
        },
        "waveform": {
            "name": "Waveform Visualisation",
            "supports_i2v": False,
            "max_duration": 60.0,
        },
    }

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__(settings=settings)
        _ensure_ffmpeg()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_output_path(self, output_path: Path | None, prefix: str) -> Path:
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            return output_path
        output_dir = Path(tempfile.gettempdir()) / "vidmation" / "videogen"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / f"local_{prefix}_{uuid.uuid4().hex[:12]}.mp4"

    def _detect_mode(self, prompt: str) -> str:
        """Infer the generation mode from prompt keywords."""
        lower = prompt.lower()
        if any(kw in lower for kw in ("title card", "text card", "stat card", "quote")):
            return "text_card"
        if any(kw in lower for kw in ("gradient", "color background", "colour background")):
            return "gradient"
        if any(kw in lower for kw in ("particle", "sparkle", "confetti")):
            return "particles"
        if any(kw in lower for kw in ("waveform", "audio wave", "visuali")):
            return "waveform"
        # Default to gradient for text-only generation
        return "gradient"

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        """Convert ``#RRGGBB`` to ``(R, G, B)``."""
        hex_color = hex_color.lstrip("#")
        return (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16),
        )

    # ------------------------------------------------------------------
    # Generation modes
    # ------------------------------------------------------------------

    def _generate_ken_burns(
        self,
        image_path: Path,
        prompt: str,
        duration: float,
        width: int,
        height: int,
        output_path: Path,
    ) -> Path:
        """Apply Ken Burns (zoom + pan) to a still image."""
        # Zoom from 1.0x to 1.25x over the duration with a slow pan.
        # We scale the image up and use crop + zoompan filter.
        fps = 30
        total_frames = int(duration * fps)

        # Determine zoom direction from prompt
        zoom_in = "zoom out" not in prompt.lower()
        if zoom_in:
            zoom_expr = "min(1+0.001*in,1.25)"
        else:
            zoom_expr = "max(1.25-0.001*in,1.0)"

        # Random pan direction
        x_drift = random.choice(["iw/2-(iw/zoom/2)+in*0.5", "iw/2-(iw/zoom/2)-in*0.5"])
        y_drift = "ih/2-(ih/zoom/2)+in*0.3"

        try:
            (
                ffmpeg.input(str(image_path), loop=1, t=duration)
                .filter(
                    "zoompan",
                    z=zoom_expr,
                    x=x_drift,
                    y=y_drift,
                    d=total_frames,
                    s=f"{width}x{height}",
                    fps=fps,
                )
                .output(
                    str(output_path),
                    vcodec="libx264",
                    pix_fmt="yuv420p",
                    t=duration,
                    r=fps,
                    movflags="+faststart",
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
        except ffmpeg.Error as e:
            self.logger.error("FFmpeg ken_burns error: %s", e.stderr.decode() if e.stderr else str(e))
            raise RuntimeError(f"Ken Burns generation failed: {e}") from e

        self.logger.info("Ken Burns clip saved: %s", output_path)
        return output_path

    def _generate_text_card(
        self,
        prompt: str,
        duration: float,
        width: int,
        height: int,
        output_path: Path,
    ) -> Path:
        """Generate an animated text card with a gradient background."""
        fps = 30
        # Extract the key text from the prompt
        text = prompt.strip()
        if len(text) > 120:
            text = text[:117] + "..."

        # Escape special characters for drawtext
        text_escaped = text.replace("'", "'\\''").replace(":", "\\:")

        # Build a colour source with animated gradient using geq
        # Then overlay text with a fade-in
        try:
            (
                ffmpeg.input(
                    f"color=c=0x1a1a2e:s={width}x{height}:d={duration}:r={fps}",
                    f="lavfi",
                )
                .filter(
                    "drawtext",
                    text=text_escaped,
                    fontsize=min(width // 15, 64),
                    fontcolor="white",
                    x="(w-text_w)/2",
                    y="(h-text_h)/2",
                    alpha=f"if(lt(t,1),t,if(gt(t,{duration - 1}),{duration}-t,1))",
                    borderw=3,
                    bordercolor="black",
                )
                .output(
                    str(output_path),
                    vcodec="libx264",
                    pix_fmt="yuv420p",
                    t=duration,
                    r=fps,
                    movflags="+faststart",
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
        except ffmpeg.Error as e:
            self.logger.error("FFmpeg text_card error: %s", e.stderr.decode() if e.stderr else str(e))
            raise RuntimeError(f"Text card generation failed: {e}") from e

        self.logger.info("Text card clip saved: %s", output_path)
        return output_path

    def _generate_gradient(
        self,
        prompt: str,
        duration: float,
        width: int,
        height: int,
        output_path: Path,
    ) -> Path:
        """Generate a smoothly animating gradient background."""
        fps = 30
        # Pick colours based on prompt keywords, otherwise random palette
        palettes = [
            ("0x667eea", "0x764ba2"),  # Purple-blue
            ("0xf093fb", "0xf5576c"),  # Pink-red
            ("0x4facfe", "0x00f2fe"),  # Blue-cyan
            ("0x43e97b", "0x38f9d7"),  # Green-teal
            ("0xfa709a", "0xfee140"),  # Pink-yellow
            ("0xa18cd1", "0xfbc2eb"),  # Lavender-pink
            ("0x667eea", "0x43e97b"),  # Blue-green
        ]
        c1, c2 = random.choice(palettes)

        # Use gradients filter (pseudo-animated via hue rotation)
        try:
            (
                ffmpeg.input(
                    f"gradients=s={width}x{height}:c0={c1}:c1={c2}:speed=0.5:d={duration}:r={fps}",
                    f="lavfi",
                )
                .filter("hue", h="t*15")
                .output(
                    str(output_path),
                    vcodec="libx264",
                    pix_fmt="yuv420p",
                    t=duration,
                    r=fps,
                    movflags="+faststart",
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
        except ffmpeg.Error:
            # Fallback: simpler approach if gradients filter not available
            self.logger.warning(
                "gradients filter not available, falling back to color source with hue rotation"
            )
            try:
                (
                    ffmpeg.input(
                        f"color=c={c1}:s={width}x{height}:d={duration}:r={fps}",
                        f="lavfi",
                    )
                    .filter("hue", h="t*30")
                    .output(
                        str(output_path),
                        vcodec="libx264",
                        pix_fmt="yuv420p",
                        t=duration,
                        r=fps,
                        movflags="+faststart",
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
            except ffmpeg.Error as e2:
                self.logger.error(
                    "FFmpeg gradient error: %s",
                    e2.stderr.decode() if e2.stderr else str(e2),
                )
                raise RuntimeError(f"Gradient generation failed: {e2}") from e2

        self.logger.info("Gradient clip saved: %s", output_path)
        return output_path

    def _generate_particles(
        self,
        prompt: str,
        duration: float,
        width: int,
        height: int,
        output_path: Path,
    ) -> Path:
        """Generate a simple particle / sparkle effect using FFmpeg life filter."""
        fps = 30

        # Use the life cellular automaton filter for organic particle-like motion
        # over a dark background
        try:
            (
                ffmpeg.input(
                    f"life=s={width}x{height}:mold=10:r={fps}:ratio=0.1:death_color=#000000FF:life_color=#FFFFFFCC",
                    f="lavfi",
                )
                .filter("scale", width, height, flags="neighbor")
                .filter("gblur", sigma=2)
                .output(
                    str(output_path),
                    vcodec="libx264",
                    pix_fmt="yuv420p",
                    t=duration,
                    r=fps,
                    movflags="+faststart",
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
        except ffmpeg.Error:
            # Fallback: use noise filter for a sparkle-like effect
            self.logger.warning(
                "life filter failed, falling back to noise-based particles"
            )
            try:
                (
                    ffmpeg.input(
                        f"color=c=black:s={width}x{height}:d={duration}:r={fps}",
                        f="lavfi",
                    )
                    .filter("noise", alls=80, allf="t")
                    .filter("gblur", sigma=1.5)
                    .filter("curves", preset="increase_contrast")
                    .output(
                        str(output_path),
                        vcodec="libx264",
                        pix_fmt="yuv420p",
                        t=duration,
                        r=fps,
                        movflags="+faststart",
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
            except ffmpeg.Error as e2:
                self.logger.error(
                    "FFmpeg particles error: %s",
                    e2.stderr.decode() if e2.stderr else str(e2),
                )
                raise RuntimeError(f"Particle generation failed: {e2}") from e2

        self.logger.info("Particles clip saved: %s", output_path)
        return output_path

    def _generate_waveform(
        self,
        prompt: str,
        duration: float,
        width: int,
        height: int,
        output_path: Path,
    ) -> Path:
        """Generate a synthetic audio-reactive waveform visualisation."""
        fps = 30

        # Generate a sine wave audio source and visualise it
        freq = 440  # Hz
        try:
            (
                ffmpeg.input(
                    f"sine=frequency={freq}:duration={duration}",
                    f="lavfi",
                )
                .filter(
                    "showwaves",
                    s=f"{width}x{height}",
                    mode="cline",
                    rate=fps,
                    colors="0x4facfe|0x00f2fe",
                )
                .output(
                    str(output_path),
                    vcodec="libx264",
                    pix_fmt="yuv420p",
                    t=duration,
                    r=fps,
                    movflags="+faststart",
                    an=None,  # No audio in output
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
        except ffmpeg.Error as e:
            self.logger.error(
                "FFmpeg waveform error: %s",
                e.stderr.decode() if e.stderr else str(e),
            )
            raise RuntimeError(f"Waveform generation failed: {e}") from e

        self.logger.info("Waveform clip saved: %s", output_path)
        return output_path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        duration: float = 5.0,
        aspect_ratio: str = "16:9",
        output_path: Path | None = None,
    ) -> Path:
        """Generate a procedural video clip from a text prompt using FFmpeg."""
        mode = self._detect_mode(prompt)
        width, height = ASPECT_RATIO_MAP.get(aspect_ratio, (1280, 720))
        dest = self._resolve_output_path(output_path, mode)

        self.logger.info(
            "Local generate: mode=%s, prompt=%r, duration=%.1fs, size=%dx%d",
            mode,
            prompt[:80],
            duration,
            width,
            height,
        )

        dispatch = {
            "text_card": lambda: self._generate_text_card(prompt, duration, width, height, dest),
            "gradient": lambda: self._generate_gradient(prompt, duration, width, height, dest),
            "particles": lambda: self._generate_particles(prompt, duration, width, height, dest),
            "waveform": lambda: self._generate_waveform(prompt, duration, width, height, dest),
        }

        handler = dispatch.get(mode)
        if handler is None:
            # Default to gradient
            return self._generate_gradient(prompt, duration, width, height, dest)
        return handler()

    def generate_from_image(
        self,
        image_path: Path,
        prompt: str,
        duration: float = 5.0,
        output_path: Path | None = None,
    ) -> Path:
        """Apply Ken Burns effect (zoom + pan) to a still image."""
        if not image_path.exists():
            raise FileNotFoundError(f"Source image not found: {image_path}")

        width, height = 1280, 720  # Default landscape
        dest = self._resolve_output_path(output_path, "ken_burns")

        self.logger.info(
            "Local I2V (Ken Burns): image=%s, prompt=%r, duration=%.1fs",
            image_path.name,
            prompt[:80],
            duration,
        )

        return self._generate_ken_burns(image_path, prompt, duration, width, height, dest)

    def list_models(self) -> list[dict]:
        """Return metadata for all local generation modes."""
        return [
            {
                "id": mode_id,
                "name": meta["name"],
                "supports_i2v": meta["supports_i2v"],
                "max_duration": meta["max_duration"],
                "cost_per_second": 0.0,
                "provider": "local",
            }
            for mode_id, meta in self.MODES.items()
        ]

    def estimate_cost(self, duration: float, model: str | None = None) -> float:
        """Local generation is free."""
        return 0.0
