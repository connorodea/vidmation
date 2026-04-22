"""Channel profile loader - YAML-based channel configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class VoiceConfig:
    provider: str = "elevenlabs"
    voice_id: str = ""
    stability: float = 0.5
    similarity_boost: float = 0.75
    speed: float = 1.0
    model: str = ""  # For Replicate/fal voice models


@dataclass
class VideoConfig:
    format: str = "landscape"
    resolution: str = "1920x1080"
    target_duration_min: int = 480
    target_duration_max: int = 900
    transition: str = "crossfade"
    caption_style: str = "bold_centered"
    caption_font: str = "Montserrat-Bold"
    caption_color: str = "#FFFFFF"
    caption_outline_color: str = "#000000"
    caption_font_size: int = 48


@dataclass
class ContentConfig:
    tone: str = "informative, engaging"
    script_style: str = "listicle"
    typical_topics: list[str] = field(default_factory=list)
    intro_hook_style: str = "question"
    cta_style: str = "gentle"


@dataclass
class MusicConfig:
    genre: str = "ambient"
    volume: float = 0.15
    source: str = "local"


@dataclass
class ThumbnailConfig:
    provider: str = "dalle"
    style: str = "cinematic, dramatic lighting, bold text overlay"
    include_text: bool = True
    text_position: str = "center"


@dataclass
class YouTubeConfig:
    visibility: str = "public"
    category_id: str = "22"
    default_language: str = "en"
    schedule: str | None = None


@dataclass
class ChannelProfile:
    name: str = "Default Channel"
    niche: str = "general"
    target_audience: str = "General audience"
    content: ContentConfig = field(default_factory=ContentConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    music: MusicConfig = field(default_factory=MusicConfig)
    thumbnail: ThumbnailConfig = field(default_factory=ThumbnailConfig)
    youtube: YouTubeConfig = field(default_factory=YouTubeConfig)


def _dict_to_dataclass(cls: type, data: dict[str, Any]) -> Any:
    """Recursively convert a dict to a nested dataclass.

    Keys present in *data* that are not fields of *cls* are silently ignored
    so that YAML profiles with extra/forward-compatible keys (e.g. ``brand_kit``,
    ``export_platforms``) do not crash on load.
    """
    known_fields = {f.name for f in cls.__dataclass_fields__.values()}
    kwargs = {}
    for key, value in data.items():
        if key not in known_fields:
            # Silently skip unrecognised top-level keys
            continue
        if isinstance(value, dict):
            # Find the actual dataclass type for nested fields
            field_type = cls.__dataclass_fields__[key].type
            # Resolve the type if it's a string annotation
            if isinstance(field_type, str):
                field_type = eval(field_type)  # noqa: S307
            kwargs[key] = _dict_to_dataclass(field_type, value)
        else:
            kwargs[key] = value
    return cls(**kwargs)


def load_profile(path: str | Path) -> ChannelProfile:
    """Load a channel profile from a YAML file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Channel profile not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    return _dict_to_dataclass(ChannelProfile, data)


def get_default_profile() -> ChannelProfile:
    """Return the default channel profile."""
    return ChannelProfile()
