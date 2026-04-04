"""Brand kit -- loadable from YAML, applies logos, watermarks, intros, outros.

A :class:`BrandKit` captures all the visual branding elements for a channel:
logo, colours, fonts, intro/outro videos, watermark, and lower-third styling.
It can be loaded from a YAML file (typically part of the channel profile) and
applied to any rendered video via :meth:`BrandKit.apply_to_video`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


# ── Supporting dataclasses ───────────────────────────────────────────────────


@dataclass
class BrandKitColors:
    """Colour palette for the brand."""

    primary: str = "#FFFFFF"
    secondary: str = "#000000"
    accent: str = "#FF5733"
    background: str = "#1A1A2E"
    text: str = "#FFFFFF"


@dataclass
class BrandKitFonts:
    """Font family configuration for the brand."""

    heading: str = "Montserrat-Bold"
    body: str = "Open Sans"
    caption: str = "Montserrat-Bold"


@dataclass
class LowerThirdStyle:
    """Styling for lower-third name/title overlays."""

    bg_color: str = "#000000CC"
    text_color: str = "#FFFFFF"
    font: str = "Montserrat-Bold"
    font_size: int = 36
    position: str = "bottom_left"  # bottom_left | bottom_center | bottom_right
    padding: int = 20
    margin_bottom: int = 80


@dataclass
class BrandKit:
    """Complete brand kit loaded from YAML configuration.

    Contains all visual branding elements that can be applied to rendered
    videos:

    - Logo overlay (position + opacity)
    - Colour palette
    - Font families
    - Intro / outro video clips
    - Watermark overlay
    - Lower-third styling
    """

    # Logo
    logo_path: str | None = None
    logo_position: str = "top_right"  # top_left | top_right | bottom_left | bottom_right | center
    logo_opacity: float = 0.8
    logo_scale: float = 0.1  # relative to video width

    # Colours
    colors: BrandKitColors = field(default_factory=BrandKitColors)

    # Fonts
    fonts: BrandKitFonts = field(default_factory=BrandKitFonts)

    # Intro / outro
    intro_video_path: str | None = None
    outro_video_path: str | None = None

    # Watermark
    watermark_path: str | None = None
    watermark_position: str = "bottom_right"
    watermark_opacity: float = 0.3

    # Lower third
    lower_third_style: LowerThirdStyle = field(default_factory=LowerThirdStyle)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    @classmethod
    def from_yaml(cls, path: str | Path) -> BrandKit:
        """Load a BrandKit from a YAML file.

        The YAML structure should mirror the dataclass fields::

            logo_path: assets/logo.png
            logo_position: top_right
            logo_opacity: 0.8
            colors:
              primary: "#FF5733"
              secondary: "#1A1A2E"
            fonts:
              heading: Montserrat-Bold
              body: Open Sans
            intro_video_path: assets/intro.mp4
            outro_video_path: assets/outro.mp4
            watermark_path: assets/watermark.png
            lower_third_style:
              bg_color: "#000000CC"
              text_color: "#FFFFFF"

        Parameters:
            path: Path to the YAML file.

        Returns:
            A populated :class:`BrandKit` instance.

        Raises:
            FileNotFoundError: If *path* does not exist.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Brand kit YAML not found: {path}")

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BrandKit:
        """Build a BrandKit from a plain dict (e.g. a sub-section of a
        channel profile YAML).

        Parameters:
            data: Dict with keys matching :class:`BrandKit` field names.

        Returns:
            A populated :class:`BrandKit` instance.
        """
        colors_data = data.get("colors", {})
        fonts_data = data.get("fonts", {})
        lt_data = data.get("lower_third_style", {})

        colors = BrandKitColors(**{
            k: v for k, v in colors_data.items()
            if k in BrandKitColors.__dataclass_fields__
        }) if colors_data else BrandKitColors()

        fonts = BrandKitFonts(**{
            k: v for k, v in fonts_data.items()
            if k in BrandKitFonts.__dataclass_fields__
        }) if fonts_data else BrandKitFonts()

        lower_third = LowerThirdStyle(**{
            k: v for k, v in lt_data.items()
            if k in LowerThirdStyle.__dataclass_fields__
        }) if lt_data else LowerThirdStyle()

        # Build top-level kwargs, excluding nested objects we already built
        skip_keys = {"colors", "fonts", "lower_third_style"}
        top_kwargs: dict[str, Any] = {}
        for key, value in data.items():
            if key in skip_keys:
                continue
            if key in cls.__dataclass_fields__:
                top_kwargs[key] = value

        return cls(
            colors=colors,
            fonts=fonts,
            lower_third_style=lower_third,
            **top_kwargs,
        )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------

    def apply_to_video(
        self,
        video_path: Path,
        output_path: Path,
    ) -> Path:
        """Apply all configured brand elements to a video.

        This method applies the following in order:

        1. Prepend intro video (if configured).
        2. Burn logo overlay (if configured).
        3. Burn watermark overlay (if configured).
        4. Append outro video (if configured).

        Parameters:
            video_path: Path to the source video.
            output_path: Where to write the branded result.

        Returns:
            Path to the branded video file.

        Raises:
            FileNotFoundError: If *video_path* or any referenced asset does
                not exist.
        """
        video_path = Path(video_path)
        output_path = Path(output_path)

        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Lazy import to avoid circular dependency at module level
        from vidmation.brand.overlays import (
            add_logo_overlay,
            add_watermark,
            concat_videos,
        )

        current_path = video_path
        work_dir = output_path.parent

        logger.info("Applying brand kit to %s", video_path.name)

        # Step 1: Logo overlay
        if self.logo_path:
            logo = Path(self.logo_path)
            if logo.exists():
                logo_out = work_dir / f"{video_path.stem}_logo.mp4"
                current_path = add_logo_overlay(
                    video_path=current_path,
                    logo_path=logo,
                    position=self.logo_position,
                    opacity=self.logo_opacity,
                    output_path=logo_out,
                    scale=self.logo_scale,
                )
                logger.info("Logo overlay applied: %s", self.logo_position)
            else:
                logger.warning("Logo file not found, skipping: %s", self.logo_path)

        # Step 2: Watermark overlay
        if self.watermark_path:
            watermark = Path(self.watermark_path)
            if watermark.exists():
                wm_out = work_dir / f"{video_path.stem}_watermark.mp4"
                current_path = add_watermark(
                    video_path=current_path,
                    watermark_path=watermark,
                    position=self.watermark_position,
                    opacity=self.watermark_opacity,
                    output_path=wm_out,
                )
                logger.info("Watermark applied: %s", self.watermark_position)
            else:
                logger.warning(
                    "Watermark file not found, skipping: %s", self.watermark_path,
                )

        # Step 3: Concat intro + main + outro
        segments: list[Path] = []

        if self.intro_video_path:
            intro = Path(self.intro_video_path)
            if intro.exists():
                segments.append(intro)
                logger.info("Intro video queued: %s", intro.name)
            else:
                logger.warning("Intro video not found, skipping: %s", self.intro_video_path)

        segments.append(current_path)

        if self.outro_video_path:
            outro = Path(self.outro_video_path)
            if outro.exists():
                segments.append(outro)
                logger.info("Outro video queued: %s", outro.name)
            else:
                logger.warning("Outro video not found, skipping: %s", self.outro_video_path)

        if len(segments) > 1:
            concat_videos(segments, output_path)
            logger.info("Intro/outro concatenation complete")
        elif current_path != output_path:
            # No concat needed -- just copy/rename
            import shutil
            shutil.copy2(str(current_path), str(output_path))

        logger.info("Brand kit application complete: %s", output_path)
        return output_path

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def get_caption_style(self) -> dict[str, Any]:
        """Return a caption style dict derived from the brand kit's fonts and colours.

        This dict is compatible with
        :func:`vidmation.video.captions_render.generate_ass_file`.
        """
        return {
            "font_name": self.fonts.caption,
            "font_size": 48,
            "primary_color": self.colors.text,
            "outline_color": self.colors.background,
            "bold": True,
        }

    def validate(self) -> list[str]:
        """Check that all referenced asset files exist.

        Returns:
            List of issue descriptions; empty if everything is valid.
        """
        issues: list[str] = []
        for attr, label in [
            ("logo_path", "Logo"),
            ("intro_video_path", "Intro video"),
            ("outro_video_path", "Outro video"),
            ("watermark_path", "Watermark"),
        ]:
            path_str = getattr(self, attr)
            if path_str and not Path(path_str).exists():
                issues.append(f"{label} file not found: {path_str}")
        return issues

    def __repr__(self) -> str:
        parts = []
        if self.logo_path:
            parts.append(f"logo={self.logo_path}")
        if self.intro_video_path:
            parts.append("intro=yes")
        if self.outro_video_path:
            parts.append("outro=yes")
        if self.watermark_path:
            parts.append("watermark=yes")
        detail = ", ".join(parts) if parts else "empty"
        return f"<BrandKit ({detail})>"
