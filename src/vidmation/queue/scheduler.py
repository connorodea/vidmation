"""Simple cron-like scheduler for automated video generation.

Reads channel profiles that include a schedule configuration and
creates video-generation jobs at the appropriate times.
"""

from __future__ import annotations

import logging
import re
import signal
import threading
import time
from datetime import datetime, timezone
from typing import Any

from vidmation.config.profiles import ChannelProfile, load_profile
from vidmation.config.settings import Settings, get_settings
from vidmation.db.engine import get_session, init_db
from vidmation.db.repos import ChannelRepo
from vidmation.queue.tasks import enqueue_video

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schedule parsing
# ---------------------------------------------------------------------------

def _parse_schedule(schedule_str: str | None) -> dict[str, Any] | None:
    """Parse a simple schedule string into a structured dict.

    Supported formats:
        ``"daily 09:00"``         — every day at 09:00 UTC
        ``"weekly mon,wed,fri 14:00"`` — specific days at 14:00 UTC
        ``"every 6h"``            — every N hours
        ``"every 30m"``           — every N minutes

    Returns:
        A dict with keys ``type``, ``hour``, ``minute``, ``days``, or
        ``interval_seconds``.  Returns ``None`` if the string is empty or
        unparseable.
    """
    if not schedule_str:
        return None

    schedule_str = schedule_str.strip().lower()

    # "every Xh" or "every Xm"
    interval_match = re.match(r"every\s+(\d+)\s*(h|m)", schedule_str)
    if interval_match:
        value = int(interval_match.group(1))
        unit = interval_match.group(2)
        seconds = value * 3600 if unit == "h" else value * 60
        return {"type": "interval", "interval_seconds": seconds}

    # "daily HH:MM"
    daily_match = re.match(r"daily\s+(\d{1,2}):(\d{2})", schedule_str)
    if daily_match:
        return {
            "type": "daily",
            "hour": int(daily_match.group(1)),
            "minute": int(daily_match.group(2)),
        }

    # "weekly mon,tue,... HH:MM"
    weekly_match = re.match(
        r"weekly\s+([\w,]+)\s+(\d{1,2}):(\d{2})", schedule_str
    )
    if weekly_match:
        day_names = weekly_match.group(1).split(",")
        day_map = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
        days = [day_map[d.strip()] for d in day_names if d.strip() in day_map]
        return {
            "type": "weekly",
            "days": days,
            "hour": int(weekly_match.group(2)),
            "minute": int(weekly_match.group(3)),
        }

    logger.warning("Could not parse schedule: %r", schedule_str)
    return None


def _schedule_is_due(schedule: dict[str, Any], last_run: datetime | None) -> bool:
    """Check whether a schedule is due to fire right now."""
    now = datetime.now(timezone.utc)

    if schedule["type"] == "interval":
        if last_run is None:
            return True
        elapsed = (now - last_run).total_seconds()
        return elapsed >= schedule["interval_seconds"]

    if schedule["type"] == "daily":
        if last_run and last_run.date() == now.date():
            return False  # Already ran today
        return now.hour == schedule["hour"] and now.minute == schedule["minute"]

    if schedule["type"] == "weekly":
        if last_run and last_run.date() == now.date():
            return False
        return (
            now.weekday() in schedule["days"]
            and now.hour == schedule["hour"]
            and now.minute == schedule["minute"]
        )

    return False


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class VideoScheduler:
    """Reads channel schedules and creates jobs at the configured times.

    Usage::

        scheduler = VideoScheduler()
        scheduler.run_forever()  # blocks
    """

    def __init__(
        self,
        settings: Settings | None = None,
        check_interval: float = 60.0,
    ) -> None:
        self.settings = settings or get_settings()
        self.check_interval = check_interval
        self._running = False
        self._last_runs: dict[str, datetime] = {}  # channel_id -> last fire time

    def run_forever(self) -> None:
        """Check schedules in a loop.  Blocks until shutdown."""
        self._running = True
        self._install_signal_handlers()
        init_db()

        logger.info(
            "Scheduler started — checking every %.0fs (Ctrl+C to stop)",
            self.check_interval,
        )

        while self._running:
            try:
                self._tick()
            except KeyboardInterrupt:
                break
            except Exception:
                logger.error("Scheduler tick error", exc_info=True)

            time.sleep(self.check_interval)

        logger.info("Scheduler stopped")

    def run_in_thread(self) -> threading.Thread:
        """Run the scheduler in a daemon thread and return it."""
        t = threading.Thread(target=self.run_forever, daemon=True, name="scheduler")
        t.start()
        return t

    def shutdown(self) -> None:
        """Signal the scheduler to stop."""
        self._running = False

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        """Single check cycle — examine all channels and fire due schedules."""
        session = get_session()
        try:
            channel_repo = ChannelRepo(session)
            channels = channel_repo.list_all(active_only=True)

            for channel in channels:
                self._check_channel(channel)
        finally:
            session.close()

    def _check_channel(self, channel) -> None:
        """Check if a channel's schedule is due and enqueue if so."""
        try:
            profile = load_profile(channel.profile_path)
        except FileNotFoundError:
            return

        schedule_str = profile.youtube.schedule
        schedule = _parse_schedule(schedule_str)
        if schedule is None:
            return

        last_run = self._last_runs.get(channel.id)

        if _schedule_is_due(schedule, last_run):
            topic = self._pick_topic(profile)
            logger.info(
                "Schedule fired for channel '%s' — topic: %r",
                channel.name,
                topic,
            )

            try:
                enqueue_video(
                    topic=topic,
                    channel_name=channel.name,
                    format=profile.video.format,
                )
                self._last_runs[channel.id] = datetime.now(timezone.utc)
            except Exception:
                logger.error(
                    "Failed to enqueue scheduled video for channel '%s'",
                    channel.name,
                    exc_info=True,
                )

    def _pick_topic(self, profile: ChannelProfile) -> str:
        """Choose the next topic for a scheduled video.

        For now, cycles through the profile's ``typical_topics`` list.
        A more sophisticated version could use an LLM to generate fresh topics.
        """
        topics = profile.content.typical_topics
        if not topics:
            return f"Trending {profile.niche} topic"

        # Simple round-robin based on current timestamp
        idx = int(time.time()) % len(topics)
        return topics[idx]

    def _install_signal_handlers(self) -> None:
        """Install SIGTERM/SIGINT handlers for graceful shutdown."""
        def _handler(signum, frame):
            sig_name = signal.Signals(signum).name
            logger.info("Scheduler received %s — shutting down", sig_name)
            self._running = False

        try:
            signal.signal(signal.SIGTERM, _handler)
            signal.signal(signal.SIGINT, _handler)
        except ValueError:
            # Can't set signal handlers outside main thread
            pass
