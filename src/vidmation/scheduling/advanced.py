"""Production-grade content scheduling system.

Replaces the basic ``queue.scheduler.VideoScheduler`` with database-backed
scheduling, cron expressions, recurring generation, and analytics-driven
optimal publish-time suggestions.
"""

from __future__ import annotations

import logging
import signal
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, update

from vidmation.config.settings import Settings, get_settings
from vidmation.db.engine import get_session, init_db
from vidmation.models.schedule import Schedule, ScheduleStatus, ScheduleType, TopicSource

logger = logging.getLogger("vidmation.scheduling.advanced")


# ---------------------------------------------------------------------------
# Cron helpers (lightweight — no external dependency)
# ---------------------------------------------------------------------------

_WEEKDAY_MAP = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def _parse_cron_field(field: str, min_val: int, max_val: int) -> list[int]:
    """Parse a single cron field into a list of matching integers.

    Supports: ``*``, ``*/N``, ``N``, ``N-M``, ``N,M,...``
    """
    if field == "*":
        return list(range(min_val, max_val + 1))

    if field.startswith("*/"):
        step = int(field[2:])
        return list(range(min_val, max_val + 1, step))

    values: list[int] = []
    for part in field.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-", 1)
            values.extend(range(int(lo), int(hi) + 1))
        else:
            # Could be a weekday name
            if part.lower() in _WEEKDAY_MAP:
                values.append(_WEEKDAY_MAP[part.lower()])
            else:
                values.append(int(part))
    return values


def _cron_matches(cron_expression: str, dt: datetime) -> bool:
    """Check if a datetime matches a cron expression.

    Format: ``minute hour day_of_month month day_of_week``
    (standard 5-field cron).
    """
    parts = cron_expression.strip().split()
    if len(parts) != 5:
        logger.warning("Invalid cron expression (need 5 fields): %r", cron_expression)
        return False

    minute_field, hour_field, dom_field, month_field, dow_field = parts

    minutes = _parse_cron_field(minute_field, 0, 59)
    hours = _parse_cron_field(hour_field, 0, 23)
    doms = _parse_cron_field(dom_field, 1, 31)
    months = _parse_cron_field(month_field, 1, 12)
    dows = _parse_cron_field(dow_field, 0, 6)

    return (
        dt.minute in minutes
        and dt.hour in hours
        and dt.day in doms
        and dt.month in months
        and dt.weekday() in dows
    )


def _next_cron_run(cron_expression: str, after: datetime) -> datetime | None:
    """Calculate the next datetime matching a cron expression.

    Scans forward minute-by-minute for up to 366 days.
    Returns None if no match is found.
    """
    candidate = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
    max_time = after + timedelta(days=366)

    while candidate < max_time:
        if _cron_matches(cron_expression, candidate):
            return candidate
        candidate += timedelta(minutes=1)

    return None


# ---------------------------------------------------------------------------
# AdvancedScheduler
# ---------------------------------------------------------------------------

class AdvancedScheduler:
    """Production-grade content scheduling system.

    Features:
        - One-time publish scheduling at specific datetimes
        - Recurring video generation via cron expressions
        - Multiple topic sources (AI, content calendar, RSS)
        - Analytics-based optimal publish time suggestions
        - Pause / resume support
        - Database-backed state (survives restarts)

    Usage::

        scheduler = AdvancedScheduler()
        scheduler.schedule_video("vid-123", publish_at=datetime(...), platforms=["youtube"])
        scheduler.schedule_recurring("my-channel", "0 14 * * 1,3,5", topic_source="ai")
        scheduler.run_forever()  # or run_in_thread()
    """

    def __init__(
        self,
        settings: Settings | None = None,
        check_interval: float = 60.0,
    ) -> None:
        self.settings = settings or get_settings()
        self.check_interval = check_interval
        self._running = False

    # ------------------------------------------------------------------
    # Schedule management
    # ------------------------------------------------------------------

    def schedule_video(
        self,
        video_id: str,
        publish_at: datetime,
        platforms: list[str] | None = None,
        channel_id: str | None = None,
    ) -> Schedule:
        """Schedule a video for publishing at a specific time.

        Args:
            video_id: ID of the video to publish.
            publish_at: When to publish (UTC).
            platforms: Target platforms (default: ``["youtube"]``).
            channel_id: Channel ID. If None, looked up from the video.

        Returns:
            The created :class:`Schedule` record.
        """
        if platforms is None:
            platforms = ["youtube"]

        session = get_session()
        try:
            # Resolve channel_id from video if not provided
            if channel_id is None:
                from vidmation.models.video import Video
                video = session.get(Video, video_id)
                if video:
                    channel_id = video.channel_id
                else:
                    raise ValueError(f"Video '{video_id}' not found")

            schedule = Schedule(
                channel_id=channel_id,
                video_id=video_id,
                schedule_type=ScheduleType.ONE_TIME,
                publish_at=publish_at,
                next_run_at=publish_at,
                platforms=platforms,
                status=ScheduleStatus.ACTIVE,
            )
            session.add(schedule)
            session.commit()
            session.refresh(schedule)

            logger.info(
                "Scheduled video %s for %s on %s",
                video_id, publish_at.isoformat(), platforms,
            )
            return schedule
        finally:
            session.close()

    def schedule_recurring(
        self,
        channel_name: str,
        cron_expression: str,
        topic_source: str = "ai",
        topic_config: dict | None = None,
        platforms: list[str] | None = None,
    ) -> Schedule:
        """Set up recurring video generation.

        Args:
            channel_name: Name of the channel to generate for.
            cron_expression: Standard 5-field cron (``min hour dom month dow``).
            topic_source: How to pick topics — ``"ai"``, ``"content_calendar"``, or ``"rss"``.
            topic_config: Source-specific configuration (RSS URL, calendar ref, etc.).
            platforms: Target platforms (default: ``["youtube"]``).

        Returns:
            The created :class:`Schedule` record.
        """
        if platforms is None:
            platforms = ["youtube"]

        session = get_session()
        try:
            from vidmation.db.repos import ChannelRepo
            channel_repo = ChannelRepo(session)
            channel = channel_repo.get_by_name(channel_name)
            if not channel:
                raise ValueError(f"Channel '{channel_name}' not found")

            now = datetime.now(timezone.utc)
            next_run = _next_cron_run(cron_expression, now)

            schedule = Schedule(
                channel_id=channel.id,
                schedule_type=ScheduleType.RECURRING,
                cron_expression=cron_expression,
                publish_at=next_run,
                next_run_at=next_run,
                platforms=platforms,
                topic_source=topic_source,
                topic_config=topic_config or {},
                status=ScheduleStatus.ACTIVE,
            )
            session.add(schedule)
            session.commit()
            session.refresh(schedule)

            logger.info(
                "Recurring schedule created for '%s': %s (next: %s)",
                channel_name, cron_expression,
                next_run.isoformat() if next_run else "unknown",
            )
            return schedule
        finally:
            session.close()

    def get_schedule(
        self,
        channel_name: str | None = None,
        include_completed: bool = False,
    ) -> list[dict]:
        """Get upcoming scheduled items.

        Args:
            channel_name: Filter to a specific channel (None = all).
            include_completed: Include completed/failed schedules.

        Returns:
            List of schedule dicts with all relevant fields.
        """
        session = get_session()
        try:
            stmt = select(Schedule).order_by(Schedule.next_run_at.asc())

            if channel_name:
                from vidmation.db.repos import ChannelRepo
                channel_repo = ChannelRepo(session)
                channel = channel_repo.get_by_name(channel_name)
                if channel:
                    stmt = stmt.where(Schedule.channel_id == channel.id)

            if not include_completed:
                stmt = stmt.where(
                    Schedule.status.in_([ScheduleStatus.ACTIVE, ScheduleStatus.PAUSED])
                )

            schedules = list(session.scalars(stmt).all())
            return [self._schedule_to_dict(s) for s in schedules]
        finally:
            session.close()

    def pause_schedule(self, schedule_id: str) -> bool:
        """Pause an active schedule."""
        session = get_session()
        try:
            schedule = session.get(Schedule, schedule_id)
            if schedule and schedule.status == ScheduleStatus.ACTIVE:
                schedule.status = ScheduleStatus.PAUSED
                session.commit()
                logger.info("Schedule %s paused", schedule_id)
                return True
            return False
        finally:
            session.close()

    def resume_schedule(self, schedule_id: str) -> bool:
        """Resume a paused schedule."""
        session = get_session()
        try:
            schedule = session.get(Schedule, schedule_id)
            if schedule and schedule.status == ScheduleStatus.PAUSED:
                schedule.status = ScheduleStatus.ACTIVE
                # Recalculate next run for recurring
                if schedule.schedule_type == ScheduleType.RECURRING and schedule.cron_expression:
                    now = datetime.now(timezone.utc)
                    schedule.next_run_at = _next_cron_run(schedule.cron_expression, now)
                session.commit()
                logger.info("Schedule %s resumed", schedule_id)
                return True
            return False
        finally:
            session.close()

    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule entirely."""
        session = get_session()
        try:
            schedule = session.get(Schedule, schedule_id)
            if schedule:
                session.delete(schedule)
                session.commit()
                logger.info("Schedule %s deleted", schedule_id)
                return True
            return False
        finally:
            session.close()

    def optimal_publish_times(self, channel_name: str) -> list[dict]:
        """Suggest optimal publish times based on analytics and best practices.

        Returns a list of ``{day_of_week, hour, score, reasoning}`` dicts
        sorted by descending score.

        Currently uses industry heuristics.  When YouTube Analytics data
        is available the scores will incorporate real audience data.
        """
        # Industry-standard optimal YouTube posting times (UTC).
        # Weighted by general engagement patterns.
        heuristic_slots = [
            {"day_of_week": "Monday",    "hour": 14, "score": 0.82, "reasoning": "Start-of-week lunchtime engagement peak"},
            {"day_of_week": "Tuesday",   "hour": 14, "score": 0.88, "reasoning": "Highest mid-week engagement window"},
            {"day_of_week": "Wednesday", "hour": 14, "score": 0.85, "reasoning": "Strong mid-week viewership"},
            {"day_of_week": "Thursday",  "hour": 12, "score": 0.86, "reasoning": "Early publishing captures afternoon viewers"},
            {"day_of_week": "Friday",    "hour": 15, "score": 0.90, "reasoning": "Pre-weekend leisure browsing peak"},
            {"day_of_week": "Saturday",  "hour": 10, "score": 0.92, "reasoning": "Weekend morning high-engagement window"},
            {"day_of_week": "Sunday",    "hour": 10, "score": 0.87, "reasoning": "Weekend morning catch-up viewing"},
            {"day_of_week": "Tuesday",   "hour": 9,  "score": 0.78, "reasoning": "Morning commute consumption"},
            {"day_of_week": "Wednesday", "hour": 9,  "score": 0.76, "reasoning": "Morning commute consumption"},
            {"day_of_week": "Friday",    "hour": 9,  "score": 0.80, "reasoning": "Pre-weekend anticipation"},
        ]

        # Try to augment with real analytics data
        try:
            session = get_session()
            try:
                from vidmation.db.repos import ChannelRepo
                channel_repo = ChannelRepo(session)
                channel = channel_repo.get_by_name(channel_name)
                if channel:
                    # Query past successful upload times and weight them
                    from vidmation.models.video import Video, VideoStatus
                    stmt = (
                        select(Video)
                        .where(
                            Video.channel_id == channel.id,
                            Video.status == VideoStatus.UPLOADED,
                        )
                        .order_by(Video.created_at.desc())
                        .limit(50)
                    )
                    uploaded_videos = list(session.scalars(stmt).all())

                    if len(uploaded_videos) >= 5:
                        # Compute hour-of-day frequency from actual uploads
                        hour_counts: dict[int, int] = {}
                        for video in uploaded_videos:
                            if video.created_at:
                                h = video.created_at.hour
                                hour_counts[h] = hour_counts.get(h, 0) + 1

                        # Boost heuristic scores for hours with real upload data
                        max_count = max(hour_counts.values()) if hour_counts else 1
                        for slot in heuristic_slots:
                            hour = slot["hour"]
                            if hour in hour_counts:
                                boost = 0.05 * (hour_counts[hour] / max_count)
                                slot["score"] = min(1.0, slot["score"] + boost)
                                slot["reasoning"] += " (boosted by channel history)"
            finally:
                session.close()
        except Exception:
            logger.debug("Could not augment with analytics data", exc_info=True)

        # Sort by score descending
        heuristic_slots.sort(key=lambda s: s["score"], reverse=True)
        return heuristic_slots

    # ------------------------------------------------------------------
    # Scheduler loop
    # ------------------------------------------------------------------

    def run_forever(self) -> None:
        """Check schedules in a loop. Blocks until shutdown."""
        self._running = True
        self._install_signal_handlers()
        init_db()

        logger.info(
            "Advanced scheduler started — checking every %.0fs (Ctrl+C to stop)",
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

        logger.info("Advanced scheduler stopped")

    def run_in_thread(self) -> threading.Thread:
        """Run the scheduler in a daemon thread and return it."""
        t = threading.Thread(
            target=self.run_forever, daemon=True, name="advanced-scheduler"
        )
        t.start()
        return t

    def shutdown(self) -> None:
        """Signal the scheduler to stop."""
        self._running = False

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        """Single check cycle — find and fire due schedules."""
        now = datetime.now(timezone.utc)
        session = get_session()
        try:
            stmt = (
                select(Schedule)
                .where(
                    Schedule.status == ScheduleStatus.ACTIVE,
                    Schedule.next_run_at <= now,
                )
                .order_by(Schedule.next_run_at.asc())
            )
            due_schedules = list(session.scalars(stmt).all())

            for schedule in due_schedules:
                self._fire_schedule(session, schedule, now)

        finally:
            session.close()

    def _fire_schedule(
        self, session: Any, schedule: Schedule, now: datetime
    ) -> None:
        """Execute a single due schedule."""
        try:
            if schedule.schedule_type == ScheduleType.ONE_TIME:
                self._fire_one_time(session, schedule, now)
            elif schedule.schedule_type == ScheduleType.RECURRING:
                self._fire_recurring(session, schedule, now)
        except Exception:
            logger.error(
                "Failed to fire schedule %s", schedule.id, exc_info=True
            )
            schedule.status = ScheduleStatus.FAILED
            schedule.error_message = "Execution error — check logs"
            session.commit()

    def _fire_one_time(
        self, session: Any, schedule: Schedule, now: datetime
    ) -> None:
        """Fire a one-time publish schedule."""
        if schedule.video_id:
            logger.info(
                "Firing one-time publish for video %s on %s",
                schedule.video_id, schedule.platforms,
            )
            try:
                from vidmation.publishing.manager import PublishManager
                publisher = PublishManager()
                publisher.publish(
                    video_id=schedule.video_id,
                    platforms=schedule.platforms or ["youtube"],
                )
            except Exception as exc:
                logger.error("Publish failed for schedule %s: %s", schedule.id, exc)
                schedule.error_message = str(exc)[:1000]

        schedule.status = ScheduleStatus.COMPLETED
        schedule.last_run_at = now
        session.commit()

    def _fire_recurring(
        self, session: Any, schedule: Schedule, now: datetime
    ) -> None:
        """Fire a recurring generation schedule."""
        logger.info(
            "Firing recurring schedule %s (cron: %s)",
            schedule.id, schedule.cron_expression,
        )

        # Pick a topic based on the configured source
        topic = self._pick_topic(session, schedule)

        # Find the channel name for enqueue_video
        from vidmation.models.channel import Channel
        channel = session.get(Channel, schedule.channel_id)
        channel_name = channel.name if channel else "default"

        # Enqueue video generation
        try:
            from vidmation.queue.tasks import enqueue_video
            enqueue_video(
                topic=topic,
                channel_name=channel_name,
            )
            logger.info(
                "Recurring schedule fired for '%s' — topic: %r",
                channel_name, topic,
            )

            # Send notification
            try:
                from vidmation.notifications.manager import NotificationManager
                notifier = NotificationManager()
                notifier.notify_schedule_fired(
                    schedule_id=schedule.id,
                    channel_name=channel_name,
                    topic=topic,
                )
            except Exception:
                logger.debug("Notification send failed", exc_info=True)

        except Exception as exc:
            logger.error(
                "Failed to enqueue video for recurring schedule %s: %s",
                schedule.id, exc,
            )
            schedule.error_message = str(exc)[:1000]

        # Update schedule state
        schedule.last_run_at = now
        if schedule.cron_expression:
            schedule.next_run_at = _next_cron_run(schedule.cron_expression, now)
        session.commit()

    def _pick_topic(self, session: Any, schedule: Schedule) -> str:
        """Select a topic based on the schedule's topic_source."""
        source = schedule.topic_source or "ai"
        config = schedule.topic_config or {}

        if source == "manual":
            # Direct topic from config
            return config.get("topic", "Trending topic")

        if source == "content_calendar":
            # Pull from a pre-defined list in config
            topics = config.get("topics", [])
            if topics:
                # Round-robin by counting past runs
                idx = 0
                if schedule.last_run_at:
                    # Simple counter based on time
                    idx = int(schedule.last_run_at.timestamp()) % len(topics)
                return topics[idx]
            return "Trending topic"

        if source == "rss":
            # Fetch latest from RSS feed
            feed_url = config.get("feed_url", "")
            if feed_url:
                return self._fetch_rss_topic(feed_url)
            return "Trending topic"

        # Default: "ai" — let the pipeline generate a topic
        from vidmation.models.channel import Channel
        channel = session.get(Channel, schedule.channel_id)
        if channel:
            try:
                from vidmation.config.profiles import load_profile
                profile = load_profile(channel.profile_path)
                topics = profile.content.typical_topics
                if topics:
                    idx = int(time.time()) % len(topics)
                    return topics[idx]
            except Exception:
                pass
            return f"Trending topic for {channel.name}"
        return "Trending topic"

    @staticmethod
    def _fetch_rss_topic(feed_url: str) -> str:
        """Fetch the latest title from an RSS feed."""
        try:
            import httpx
            response = httpx.get(feed_url, timeout=10.0)
            response.raise_for_status()

            # Very simple XML parsing for <title> tags
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.text)

            # Try RSS 2.0 format
            for item in root.iter("item"):
                title_elem = item.find("title")
                if title_elem is not None and title_elem.text:
                    return title_elem.text.strip()

            # Try Atom format
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
                title_elem = entry.find("atom:title", ns) or entry.find(
                    "{http://www.w3.org/2005/Atom}title"
                )
                if title_elem is not None and title_elem.text:
                    return title_elem.text.strip()

        except Exception:
            logger.warning("Failed to fetch RSS topic from %s", feed_url, exc_info=True)

        return "Trending topic"

    def _install_signal_handlers(self) -> None:
        """Install SIGTERM/SIGINT handlers for graceful shutdown."""
        def _handler(signum, frame):
            sig_name = signal.Signals(signum).name
            logger.info("Advanced scheduler received %s — shutting down", sig_name)
            self._running = False

        try:
            signal.signal(signal.SIGTERM, _handler)
            signal.signal(signal.SIGINT, _handler)
        except ValueError:
            pass  # Can't set signal handlers outside main thread

    @staticmethod
    def _schedule_to_dict(schedule: Schedule) -> dict:
        """Convert a Schedule ORM object to a plain dict."""
        return {
            "id": schedule.id,
            "channel_id": schedule.channel_id,
            "video_id": schedule.video_id,
            "schedule_type": schedule.schedule_type.value,
            "cron_expression": schedule.cron_expression,
            "publish_at": schedule.publish_at.isoformat() if schedule.publish_at else None,
            "platforms": schedule.platforms or [],
            "topic_source": schedule.topic_source,
            "topic_config": schedule.topic_config,
            "status": schedule.status.value,
            "last_run_at": schedule.last_run_at.isoformat() if schedule.last_run_at else None,
            "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None,
            "error_message": schedule.error_message,
            "created_at": schedule.created_at.isoformat() if schedule.created_at else None,
        }
