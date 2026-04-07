"""Multi-platform exporter -- takes one master video and outputs platform-specific
versions for YouTube, TikTok, Instagram, etc.

Uses ffmpeg for all reformatting (crop, scale, pad, re-encode) and optionally
applies brand-kit overlays (intro/outro, logo, watermark) and platform-specific
caption styles.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from vidmation.config.profiles import ChannelProfile
from vidmation.platforms.base import Platform, PlatformType
from vidmation.platforms.facebook import FacebookPlatform
from vidmation.platforms.instagram import InstagramPlatform
from vidmation.platforms.tiktok import TikTokPlatform
from vidmation.platforms.twitter import TwitterPlatform
from vidmation.platforms.youtube import YouTubePlatform

logger = logging.getLogger(__name__)

# ── Platform name -> constructor mapping ─────────────────────────────────────

_PLATFORM_CONSTRUCTORS: dict[str, type[Platform] | tuple[type[Platform], dict[str, Any]]] = {
    "youtube": YouTubePlatform,
    "youtube_shorts": (YouTubePlatform, {"shorts": True}),
    "tiktok": TikTokPlatform,
    "instagram_reels": (InstagramPlatform, {"sub_format": "reels"}),
    "instagram_feed": (InstagramPlatform, {"sub_format": "feed"}),
    "instagram_stories": (InstagramPlatform, {"sub_format": "stories"}),
    "facebook": FacebookPlatform,
    "facebook_square": (FacebookPlatform, {"sub_format": "square"}),
    "twitter": TwitterPlatform,
}

# Short aliases for convenience
_PLATFORM_ALIASES: dict[str, str] = {
    "yt": "youtube",
    "yt_shorts": "youtube_shorts",
    "shorts": "youtube_shorts",
    "tt": "tiktok",
    "ig": "instagram_reels",
    "ig_reels": "instagram_reels",
    "ig_feed": "instagram_feed",
    "ig_stories": "instagram_stories",
    "reels": "instagram_reels",
    "stories": "instagram_stories",
    "fb": "facebook",
    "fb_square": "facebook_square",
    "x": "twitter",
    "tweet": "twitter",
}


def _resolve_platform_name(name: str) -> str:
    """Normalise a platform name, resolving aliases."""
    key = name.lower().strip().replace("-", "_").replace(" ", "_")
    return _PLATFORM_ALIASES.get(key, key)


def _build_platform(name: str) -> Platform:
    """Instantiate a :class:`Platform` by canonical name.

    Raises:
        ValueError: If *name* is not a recognised platform.
    """
    canonical = _resolve_platform_name(name)
    entry = _PLATFORM_CONSTRUCTORS.get(canonical)

    if entry is None:
        valid = ", ".join(sorted(_PLATFORM_CONSTRUCTORS))
        raise ValueError(
            f"Unknown platform '{name}'. Valid platforms: {valid}"
        )

    if isinstance(entry, tuple):
        cls, kwargs = entry
        return cls(**kwargs)
    return entry()


class MultiPlatformExporter:
    """Export a single master video to multiple platforms in one call.

    Usage::

        exporter = MultiPlatformExporter(output_dir=Path("/tmp/exports"))
        results = exporter.export(
            video_path=Path("master.mp4"),
            platforms=["youtube", "tiktok", "instagram_reels"],
            profile=my_channel_profile,
        )
        # results == {"youtube": Path(...), "tiktok": Path(...), ...}
    """

    def __init__(
        self,
        output_dir: Path | None = None,
        *,
        brand_kit: Any | None = None,
    ) -> None:
        """Initialise the exporter.

        Parameters:
            output_dir: Base directory for all platform-specific outputs.  If
                ``None``, outputs are placed alongside the source video.
            brand_kit: Optional :class:`~vidmation.brand.kit.BrandKit` instance.
                When provided, the brand kit's intro, outro, logo, and watermark
                are applied before platform reformatting.
        """
        self.output_dir = Path(output_dir) if output_dir else None
        self.brand_kit = brand_kit
        self.logger = logging.getLogger("vidmation.platforms.MultiPlatformExporter")

    def export(
        self,
        video_path: Path,
        platforms: list[str],
        profile: ChannelProfile | None = None,
        *,
        options: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Path]:
        """Export *video_path* for each platform in *platforms*.

        Parameters:
            video_path: Path to the master (source) video.
            platforms: List of platform names (e.g. ``["youtube", "tiktok"]``).
                Aliases like ``"yt"``, ``"tt"``, ``"ig"`` are accepted.
            profile: Optional :class:`ChannelProfile` -- currently used for
                logging context; future use will drive per-channel caption
                styles and metadata defaults.
            options: Per-platform option dicts keyed by platform name.
                Example: ``{"tiktok": {"crop_mode": "pillarbox"}}``.

        Returns:
            Dict mapping canonical platform name to the output file path.

        Raises:
            FileNotFoundError: If *video_path* does not exist.
            ValueError: If *platforms* is empty or contains unknown names.
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Master video not found: {video_path}")

        if not platforms:
            raise ValueError("At least one platform must be specified")

        options = options or {}
        results: dict[str, Path] = {}

        channel_name = profile.name if profile else "unknown"
        self.logger.info(
            "Multi-platform export started: %d platform(s) for channel '%s'",
            len(platforms), channel_name,
        )

        # Apply brand kit to master video if configured
        branded_path = self._apply_brand_kit(video_path)

        for platform_name in platforms:
            canonical = _resolve_platform_name(platform_name)
            platform_opts = options.get(canonical, options.get(platform_name, {}))

            self.logger.info("Exporting for platform: %s", canonical)

            try:
                platform = _build_platform(canonical)

                # Determine output path
                out_path: Path | None = None
                if self.output_dir:
                    platform_dir = self.output_dir / canonical
                    platform_dir.mkdir(parents=True, exist_ok=True)
                    out_path = platform_dir / f"{video_path.stem}_{canonical}.mp4"

                result_path = platform.format_for_platform(
                    branded_path,
                    output_path=out_path,
                    options=platform_opts,
                )
                results[canonical] = result_path

                # Validate the output
                issues = platform.validate_for_platform(result_path)
                if issues:
                    self.logger.warning(
                        "Validation issues for %s: %s",
                        canonical, "; ".join(issues),
                    )
                else:
                    self.logger.info(
                        "Platform %s: export validated successfully", canonical,
                    )

            except Exception:
                self.logger.exception(
                    "Failed to export for platform '%s'", canonical,
                )
                raise

        self.logger.info(
            "Multi-platform export complete: %d/%d platforms succeeded",
            len(results), len(platforms),
        )
        return results

    def export_all(
        self,
        video_path: Path,
        profile: ChannelProfile | None = None,
        *,
        options: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Path]:
        """Export *video_path* for every supported platform.

        Convenience method equivalent to calling :meth:`export` with all
        canonical platform names.

        Parameters:
            video_path: Path to the master video.
            profile: Optional channel profile.
            options: Per-platform option overrides.

        Returns:
            Dict mapping platform name to output file path.
        """
        all_platforms = list(_PLATFORM_CONSTRUCTORS.keys())
        return self.export(video_path, all_platforms, profile, options=options)

    def get_supported_platforms(self) -> list[str]:
        """Return a sorted list of all supported canonical platform names."""
        return sorted(_PLATFORM_CONSTRUCTORS.keys())

    def get_platform_info(self, platform_name: str) -> dict[str, Any]:
        """Return metadata spec and validation constraints for a platform.

        Parameters:
            platform_name: Platform name or alias.

        Returns:
            The platform's metadata specification dict.
        """
        platform = _build_platform(platform_name)
        return platform.get_metadata_spec()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _apply_brand_kit(self, video_path: Path) -> Path:
        """Apply brand-kit overlays to the master video if a kit is configured.

        Returns the branded video path, or the original path if no kit is set.
        """
        if self.brand_kit is None:
            return video_path

        try:
            # Lazy import to avoid circular dependency
            from vidmation.brand.kit import BrandKit

            if isinstance(self.brand_kit, BrandKit):
                out_dir = self.output_dir or video_path.parent
                branded_path = out_dir / f"{video_path.stem}_branded.mp4"
                result = self.brand_kit.apply_to_video(video_path, branded_path)
                self.logger.info("Brand kit applied: %s", result)
                return result
        except ImportError:
            self.logger.warning(
                "Brand kit provided but vidmation.brand module not available"
            )

        return video_path
