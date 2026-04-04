"""Series manager — track and manage multi-episode video series."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from vidmation.config.settings import get_settings

logger = logging.getLogger(__name__)


class SeriesManager:
    """Track multi-episode series with continuity, numbering, and branding.

    Series are stored as JSON files in ``data/series/``.  Each series file
    contains the series metadata and an ordered list of episodes.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._series_dir = self.settings.data_dir / "series"
        self._series_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _series_path(self, series_id: str) -> Path:
        return self._series_dir / f"{series_id}.json"

    def _load_series(self, series_id: str) -> dict[str, Any]:
        fp = self._series_path(series_id)
        if not fp.exists():
            raise FileNotFoundError(f"Series '{series_id}' not found")
        return json.loads(fp.read_text(encoding="utf-8"))

    def _save_series(self, data: dict[str, Any]) -> Path:
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        fp = self._series_path(data["id"])
        fp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        logger.info("Series saved: %s", fp)
        return fp

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_series(
        self,
        name: str,
        description: str = "",
        channel_name: str = "",
        episode_topics: list[str] | None = None,
        thumbnail_style: str = "",
        branding: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create a new series.

        Args:
            name: Series name (e.g., "Crypto Deep Dives").
            description: High-level series description.
            channel_name: Associated channel name.
            episode_topics: Optional pre-planned episode topics.
            thumbnail_style: Consistent thumbnail prompt fragment for
                the series (e.g., "dark blue gradient, bold white text,
                episode number badge").
            branding: Extra branding metadata (colours, fonts, etc.).

        Returns:
            The full series dict.
        """
        series_id = str(uuid.uuid4())
        episodes: list[dict] = []
        if episode_topics:
            for idx, topic in enumerate(episode_topics, 1):
                episodes.append(self._make_episode(idx, topic))

        data: dict[str, Any] = {
            "id": series_id,
            "name": name,
            "description": description,
            "channel_name": channel_name,
            "thumbnail_style": thumbnail_style,
            "branding": branding or {},
            "episodes": episodes,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        self._save_series(data)
        logger.info("Created series %r (id=%s, %d episodes)", name, series_id, len(episodes))
        return data

    def get_series(self, series_id: str) -> dict[str, Any]:
        """Get a series by ID."""
        return self._load_series(series_id)

    def list_series(self, channel_name: str | None = None) -> list[dict[str, Any]]:
        """List all series, optionally filtered by channel.

        Returns a list of summary dicts:
        ``[{id, name, channel_name, episode_count, completed_count}]``
        """
        results: list[dict[str, Any]] = []
        for fp in sorted(self._series_dir.glob("*.json")):
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue

            if channel_name and data.get("channel_name") != channel_name:
                continue

            episodes = data.get("episodes", [])
            completed = sum(1 for e in episodes if e.get("status") == "completed")

            results.append({
                "id": data["id"],
                "name": data.get("name", "Untitled"),
                "description": data.get("description", ""),
                "channel_name": data.get("channel_name", ""),
                "episode_count": len(episodes),
                "completed_count": completed,
                "created_at": data.get("created_at", ""),
            })

        return results

    def delete_series(self, series_id: str) -> bool:
        """Delete a series file.  Returns True if it existed."""
        fp = self._series_path(series_id)
        if fp.exists():
            fp.unlink()
            logger.info("Deleted series %s", series_id)
            return True
        return False

    # ------------------------------------------------------------------
    # Episode management
    # ------------------------------------------------------------------

    @staticmethod
    def _make_episode(
        number: int,
        topic: str,
        title: str = "",
    ) -> dict[str, Any]:
        return {
            "id": str(uuid.uuid4()),
            "number": number,
            "topic": topic,
            "title": title or f"Episode {number}: {topic}",
            "status": "planned",
            "video_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def add_episode(
        self,
        series_id: str,
        topic: str,
        title: str = "",
        position: int | None = None,
    ) -> dict[str, Any]:
        """Add an episode to a series.

        Args:
            series_id: Series UUID.
            topic: Episode topic.
            title: Optional custom title.  Auto-generated if empty.
            position: Insert at this episode number.  If ``None``,
                appends to the end.

        Returns:
            The new episode dict.
        """
        data = self._load_series(series_id)
        episodes = data.get("episodes", [])

        if position is None:
            number = len(episodes) + 1
        else:
            number = position

        episode = self._make_episode(number, topic, title)

        if position is not None and position <= len(episodes):
            episodes.insert(position - 1, episode)
            # Re-number subsequent episodes
            self._renumber_episodes(episodes)
        else:
            episodes.append(episode)

        data["episodes"] = episodes
        self._save_series(data)
        logger.info(
            "Added episode %d to series %s: %r",
            episode["number"],
            series_id,
            topic,
        )
        return episode

    def remove_episode(self, series_id: str, episode_id: str) -> bool:
        """Remove an episode and re-number remaining ones."""
        data = self._load_series(series_id)
        before = len(data.get("episodes", []))
        data["episodes"] = [
            e for e in data.get("episodes", []) if e.get("id") != episode_id
        ]
        if len(data["episodes"]) == before:
            return False
        self._renumber_episodes(data["episodes"])
        self._save_series(data)
        return True

    def mark_episode_completed(
        self,
        series_id: str,
        episode_id: str,
        video_id: str | None = None,
    ) -> bool:
        """Mark an episode as completed, optionally linking it to a video."""
        data = self._load_series(series_id)
        for ep in data.get("episodes", []):
            if ep.get("id") == episode_id:
                ep["status"] = "completed"
                ep["completed_at"] = datetime.now(timezone.utc).isoformat()
                if video_id:
                    ep["video_id"] = video_id
                self._save_series(data)
                return True
        return False

    def get_next_episode(self, series_id: str) -> dict[str, Any] | None:
        """Get the next planned (not completed) episode in a series."""
        data = self._load_series(series_id)
        for ep in data.get("episodes", []):
            if ep.get("status") in ("planned", "pending"):
                return ep
        return None

    def get_episode_context(self, series_id: str, episode_id: str) -> dict[str, Any]:
        """Get context for an episode to ensure series continuity.

        Returns a dict with the series name, description, previous
        episode summaries, and the current episode details — suitable
        for feeding to the script generator.
        """
        data = self._load_series(series_id)
        episodes = data.get("episodes", [])
        current = None
        previous: list[dict] = []

        for ep in episodes:
            if ep.get("id") == episode_id:
                current = ep
                break
            previous.append({
                "number": ep.get("number"),
                "title": ep.get("title", ""),
                "topic": ep.get("topic", ""),
                "status": ep.get("status", ""),
            })

        return {
            "series_name": data.get("name", ""),
            "series_description": data.get("description", ""),
            "thumbnail_style": data.get("thumbnail_style", ""),
            "branding": data.get("branding", {}),
            "total_episodes": len(episodes),
            "previous_episodes": previous,
            "current_episode": current,
        }

    # ------------------------------------------------------------------
    # Thumbnail helpers
    # ------------------------------------------------------------------

    def get_thumbnail_prompt(self, series_id: str, episode_number: int) -> str:
        """Generate a thumbnail prompt with consistent series branding.

        Combines the series ``thumbnail_style`` with episode-specific
        details to produce a prompt for the image generator.
        """
        data = self._load_series(series_id)
        style = data.get("thumbnail_style", "")
        name = data.get("name", "Series")

        # Find the episode
        episode_title = f"Episode {episode_number}"
        for ep in data.get("episodes", []):
            if ep.get("number") == episode_number:
                episode_title = ep.get("title", episode_title)
                break

        parts = [
            f"YouTube thumbnail for \"{name}\"",
            f"Episode {episode_number}: {episode_title}",
        ]
        if style:
            parts.append(f"Style: {style}")
        parts.append(
            f"Include a clear episode number badge showing 'EP {episode_number}'"
        )

        return ".  ".join(parts)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _renumber_episodes(episodes: list[dict]) -> None:
        """Re-assign sequential episode numbers after insert / delete."""
        for idx, ep in enumerate(episodes, 1):
            ep["number"] = idx
            # Update auto-generated titles
            if ep.get("title", "").startswith("Episode "):
                ep["title"] = f"Episode {idx}: {ep.get('topic', 'Untitled')}"
