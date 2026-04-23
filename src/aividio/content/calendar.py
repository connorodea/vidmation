"""Content calendar persistence and management."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from aividio.config.settings import get_settings

logger = logging.getLogger(__name__)

# iCal template fragments
_VCALENDAR_HEADER = """\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AIVIDIO//Content Calendar//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:AIVIDIO Content Calendar
"""

_VEVENT_TEMPLATE = """\
BEGIN:VEVENT
UID:{uid}
DTSTART;VALUE=DATE:{dtstart}
SUMMARY:{summary}
DESCRIPTION:{description}
CATEGORIES:{categories}
STATUS:{status}
END:VEVENT
"""

_VCALENDAR_FOOTER = "END:VCALENDAR\n"


class ContentCalendar:
    """Manage a persistent content calendar backed by JSON files.

    Each calendar is stored as a JSON file in the data directory. Entries
    can be marked as completed, skipped, or pending, and the calendar
    can be exported to iCal format for external calendar apps.
    """

    VALID_STATUSES = ("pending", "completed", "skipped", "generating", "queued")

    def __init__(self, calendar_id: str | None = None) -> None:
        self.settings = get_settings()
        self._calendars_dir = self.settings.data_dir / "calendars"
        self._calendars_dir.mkdir(parents=True, exist_ok=True)

        self.calendar_id = calendar_id or str(uuid.uuid4())
        self._file_path = self._calendars_dir / f"{self.calendar_id}.json"
        self._data: dict[str, Any] = self._load_or_init()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_or_init(self) -> dict[str, Any]:
        """Load existing calendar or initialise a new one."""
        if self._file_path.exists():
            try:
                return json.loads(self._file_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load calendar %s: %s", self._file_path, exc)

        return {
            "id": self.calendar_id,
            "channel_name": "",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "entries": [],
        }

    def save(self) -> Path:
        """Persist the calendar to disk."""
        self._data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._file_path.write_text(
            json.dumps(self._data, indent=2, default=str),
            encoding="utf-8",
        )
        logger.info("Calendar saved: %s", self._file_path)
        return self._file_path

    @property
    def file_path(self) -> Path:
        return self._file_path

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @property
    def channel_name(self) -> str:
        return self._data.get("channel_name", "")

    @channel_name.setter
    def channel_name(self, value: str) -> None:
        self._data["channel_name"] = value

    @property
    def entries(self) -> list[dict]:
        return self._data.get("entries", [])

    def add_entries(self, entries: list[dict]) -> None:
        """Add entries to the calendar.

        Each entry should have at minimum: date, topic, title.
        An ``id`` and ``status`` field will be added automatically if missing.
        """
        for entry in entries:
            if "id" not in entry:
                entry["id"] = str(uuid.uuid4())
            if "status" not in entry:
                entry["status"] = "pending"
            self._data.setdefault("entries", []).append(entry)
        logger.info("Added %d entries to calendar %s", len(entries), self.calendar_id)

    def get_entry(self, entry_id: str) -> dict | None:
        """Get a single entry by ID."""
        for entry in self.entries:
            if entry.get("id") == entry_id:
                return entry
        return None

    def update_entry(self, entry_id: str, updates: dict) -> bool:
        """Update fields on a calendar entry.

        Returns True if the entry was found and updated.
        """
        for entry in self.entries:
            if entry.get("id") == entry_id:
                entry.update(updates)
                return True
        return False

    def remove_entry(self, entry_id: str) -> bool:
        """Remove an entry from the calendar."""
        before = len(self.entries)
        self._data["entries"] = [
            e for e in self.entries if e.get("id") != entry_id
        ]
        return len(self._data["entries"]) < before

    # ------------------------------------------------------------------
    # Status management
    # ------------------------------------------------------------------

    def mark_status(self, entry_id: str, status: str) -> bool:
        """Mark an entry as completed, skipped, generating, or queued.

        Args:
            entry_id: Calendar entry UUID.
            status: One of ``pending``, ``completed``, ``skipped``,
                    ``generating``, ``queued``.

        Returns:
            True if the entry was found and updated.
        """
        if status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'.  Must be one of {self.VALID_STATUSES}"
            )
        return self.update_entry(entry_id, {"status": status})

    def mark_completed(self, entry_id: str, video_id: str | None = None) -> bool:
        """Mark an entry as completed, optionally linking to a video ID."""
        updates: dict[str, Any] = {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        if video_id:
            updates["video_id"] = video_id
        return self.update_entry(entry_id, updates)

    def mark_skipped(self, entry_id: str, reason: str = "") -> bool:
        """Mark an entry as skipped with an optional reason."""
        return self.update_entry(
            entry_id,
            {"status": "skipped", "skip_reason": reason},
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_pending(self) -> list[dict]:
        """Return all pending entries, sorted by date."""
        pending = [e for e in self.entries if e.get("status") == "pending"]
        pending.sort(key=lambda e: e.get("date", ""))
        return pending

    def get_by_date(self, target_date: date) -> list[dict]:
        """Return entries for a specific date."""
        target_str = target_date.isoformat()
        return [e for e in self.entries if e.get("date") == target_str]

    def get_by_week(self, year: int, week: int) -> list[dict]:
        """Return entries for a specific ISO week."""
        results: list[dict] = []
        for entry in self.entries:
            try:
                entry_date = datetime.strptime(entry["date"], "%Y-%m-%d").date()
                iso_year, iso_week, _ = entry_date.isocalendar()
                if iso_year == year and iso_week == week:
                    results.append(entry)
            except (KeyError, ValueError):
                continue
        results.sort(key=lambda e: e.get("date", ""))
        return results

    def get_stats(self) -> dict[str, int]:
        """Return entry counts by status."""
        stats: dict[str, int] = {"total": len(self.entries)}
        for status in self.VALID_STATUSES:
            stats[status] = sum(
                1 for e in self.entries if e.get("status") == status
            )
        return stats

    # ------------------------------------------------------------------
    # Queue integration
    # ------------------------------------------------------------------

    def enqueue_pending(self, limit: int | None = None) -> list[dict]:
        """Auto-enqueue pending items that are due today or earlier.

        Marks each entry as ``queued`` and returns the list of entries
        that should be sent to the video generation queue.

        This method does NOT commit to the database — the caller is
        responsible for calling :func:`aividio.queue.tasks.enqueue_video`
        for each returned entry and then calling :meth:`save`.
        """
        today = date.today().isoformat()
        due = [
            e
            for e in self.entries
            if e.get("status") == "pending" and e.get("date", "9999") <= today
        ]
        due.sort(key=lambda e: e.get("date", ""))

        if limit is not None:
            due = due[:limit]

        for entry in due:
            entry["status"] = "queued"
            entry["queued_at"] = datetime.now(timezone.utc).isoformat()

        if due:
            logger.info("Queued %d calendar entries for generation", len(due))

        return due

    # ------------------------------------------------------------------
    # iCal export
    # ------------------------------------------------------------------

    def export_ical(self, output_path: str | Path | None = None) -> str:
        """Export the calendar to iCal (.ics) format.

        Args:
            output_path: Optional file path.  If provided, the iCal
                content is written there.

        Returns:
            The iCal content as a string.
        """
        events: list[str] = []
        for entry in self.entries:
            entry_date = entry.get("date", date.today().isoformat())
            dtstart = entry_date.replace("-", "")

            summary = entry.get("title", entry.get("topic", "Untitled"))
            # Escape special chars for iCal
            summary = summary.replace(",", "\\,").replace(";", "\\;")

            desc_parts = []
            if entry.get("topic"):
                desc_parts.append(f"Topic: {entry['topic']}")
            if entry.get("format"):
                desc_parts.append(f"Format: {entry['format']}")
            if entry.get("content_type"):
                desc_parts.append(f"Type: {entry['content_type']}")
            if entry.get("keywords"):
                kw = entry["keywords"]
                if isinstance(kw, list):
                    kw = ", ".join(kw)
                desc_parts.append(f"Keywords: {kw}")
            if entry.get("notes"):
                desc_parts.append(f"Notes: {entry['notes']}")
            description = "\\n".join(desc_parts)

            status_map = {
                "pending": "TENTATIVE",
                "queued": "TENTATIVE",
                "generating": "TENTATIVE",
                "completed": "CONFIRMED",
                "skipped": "CANCELLED",
            }
            ical_status = status_map.get(entry.get("status", "pending"), "TENTATIVE")

            categories = entry.get("content_type", "video").upper()

            events.append(
                _VEVENT_TEMPLATE.format(
                    uid=entry.get("id", str(uuid.uuid4())),
                    dtstart=dtstart,
                    summary=summary,
                    description=description,
                    categories=categories,
                    status=ical_status,
                )
            )

        ical = _VCALENDAR_HEADER + "".join(events) + _VCALENDAR_FOOTER

        if output_path:
            output_path = Path(output_path)
            output_path.write_text(ical, encoding="utf-8")
            logger.info("iCal exported to %s", output_path)

        return ical

    # ------------------------------------------------------------------
    # Class-level helpers
    # ------------------------------------------------------------------

    @classmethod
    def list_calendars(cls, data_dir: Path | None = None) -> list[dict]:
        """List all saved calendars with basic metadata.

        Returns:
            ``[{id, channel_name, created_at, entry_count, file_path}]``
        """
        settings = get_settings()
        calendars_dir = (data_dir or settings.data_dir) / "calendars"
        if not calendars_dir.exists():
            return []

        results: list[dict] = []
        for fp in sorted(calendars_dir.glob("*.json")):
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
                results.append({
                    "id": data.get("id", fp.stem),
                    "channel_name": data.get("channel_name", ""),
                    "created_at": data.get("created_at", ""),
                    "entry_count": len(data.get("entries", [])),
                    "file_path": str(fp),
                })
            except (json.JSONDecodeError, OSError):
                continue
        return results

    @classmethod
    def load(cls, calendar_id: str) -> ContentCalendar:
        """Load an existing calendar by ID."""
        cal = cls(calendar_id=calendar_id)
        if not cal._file_path.exists():
            raise FileNotFoundError(f"Calendar '{calendar_id}' not found")
        return cal
