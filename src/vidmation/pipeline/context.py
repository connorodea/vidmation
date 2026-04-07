"""Pipeline context — shared mutable state flowing through pipeline stages."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from vidmation.config.profiles import ChannelProfile
from vidmation.models.video import VideoFormat


@dataclass
class PipelineContext:
    """Shared mutable state that flows through every pipeline stage.

    Each stage reads what it needs and writes its outputs here.  The context
    can be serialised to JSON so a pipeline can be resumed from the last
    successful stage after a failure.
    """

    video_id: str
    channel_profile: ChannelProfile
    topic: str
    format: VideoFormat
    work_dir: Path

    # --- Accumulated during pipeline ---
    script: dict | None = None
    voiceover_path: Path | None = None
    voiceover_duration: float | None = None
    word_timestamps: list[dict] | None = None
    media_clips: list[dict] | None = None  # [{path, paths, section_index, type, clip_count}]
    music_path: Path | None = None
    final_video_path: Path | None = None
    thumbnail_path: Path | None = None

    # --- State tracking ---
    current_stage: str = ""
    completed_stages: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Serialisation helpers (for resume / debugging)
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialise context to a JSON-safe dictionary."""
        data = asdict(self)
        # Convert Path objects to strings
        for key, value in data.items():
            if isinstance(value, Path):
                data[key] = str(value)
        # Convert nested Path values in media_clips
        if data.get("media_clips"):
            for clip in data["media_clips"]:
                if "path" in clip and isinstance(clip["path"], Path):
                    clip["path"] = str(clip["path"])
                # Also convert paths in the multi-clip "paths" list
                if "paths" in clip and isinstance(clip["paths"], list):
                    clip["paths"] = [
                        str(p) if isinstance(p, Path) else p
                        for p in clip["paths"]
                    ]
        # VideoFormat enum -> value
        if isinstance(data.get("format"), VideoFormat):
            data["format"] = data["format"].value
        elif hasattr(data.get("format"), "value"):
            data["format"] = data["format"]
        return data

    def to_json(self) -> str:
        """Serialise context to a JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)

    def save(self, path: Path | None = None) -> Path:
        """Persist context to a JSON file inside the work directory.

        Returns:
            The path to the saved file.
        """
        target = path or (self.work_dir / "pipeline_context.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_json(), encoding="utf-8")
        return target
