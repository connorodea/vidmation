"""File and path management utilities."""

from __future__ import annotations

import tempfile
from pathlib import Path

from aividio.config.settings import get_settings


def get_work_dir(video_id: str) -> Path:
    """Get or create a working directory for a video's pipeline artifacts."""
    settings = get_settings()
    work_dir = settings.data_dir / "work" / video_id
    work_dir.mkdir(parents=True, exist_ok=True)
    return work_dir


def get_output_path(video_id: str, filename: str) -> Path:
    """Get the output path for a finished video."""
    settings = get_settings()
    output_dir = settings.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{video_id}_{filename}"


def create_temp_dir(prefix: str = "aividio_") -> Path:
    """Create a temporary directory that persists until manually cleaned."""
    return Path(tempfile.mkdtemp(prefix=prefix))


def ensure_dir(path: Path) -> Path:
    """Ensure a directory exists, creating it if necessary."""
    path.mkdir(parents=True, exist_ok=True)
    return path
