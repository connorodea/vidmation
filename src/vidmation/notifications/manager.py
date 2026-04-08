"""Central notification manager — dispatches events to all configured channels.

Usage::

    from vidmation.notifications.manager import NotificationManager

    notifier = NotificationManager()
    notifier.notify_video_complete(video_id="abc123")
    notifier.notify_job_failed(job_id="xyz789", error="OOM during render")
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from vidmation.db.engine import get_session
from vidmation.models.notification import Notification
from vidmation.notifications.discord import DiscordNotifier
from vidmation.notifications.email import EmailNotifier
from vidmation.notifications.slack import SlackNotifier

logger = logging.getLogger("vidmation.notifications.manager")


class NotificationManager:
    """Multi-channel notification system.

    On instantiation, each channel (email, Discord, Slack) is initialised.
    Channels that are not configured (missing env vars) are silently skipped
    when sending.  Every notification is persisted to the database for the
    in-app notification centre regardless of external channel delivery.
    """

    def __init__(self) -> None:
        self._email = EmailNotifier()
        self._discord = DiscordNotifier()
        self._slack = SlackNotifier()

    # ------------------------------------------------------------------
    # Core dispatch
    # ------------------------------------------------------------------

    def notify(
        self,
        event: str,
        title: str,
        message: str,
        data: dict | None = None,
    ) -> Notification:
        """Send notification via all configured channels and persist to DB.

        Args:
            event: Canonical event name (e.g. ``video_complete``).
            title: Short human-readable title.
            message: Longer description of the event.
            data: Optional structured payload (video_id, url, error, etc.).

        Returns:
            The persisted :class:`Notification` record.
        """
        channels_sent: list[str] = ["in_app"]  # always stored in DB

        # Dispatch to external channels
        if self._email.is_configured:
            if self._email.send(event, title, message, data):
                channels_sent.append("email")

        if self._discord.is_configured:
            if self._discord.send(event, title, message, data):
                channels_sent.append("discord")

        if self._slack.is_configured:
            if self._slack.send(event, title, message, data):
                channels_sent.append("slack")

        # Persist to database
        notification = self._persist(event, title, message, data, channels_sent)

        logger.info(
            "Notification [%s] dispatched to %s: %s",
            event,
            channels_sent,
            title,
        )
        return notification

    # ------------------------------------------------------------------
    # Convenience methods for common events
    # ------------------------------------------------------------------

    def notify_video_complete(self, video_id: str, title: str | None = None) -> Notification:
        """Notify that a video has finished generating."""
        notif_title = title or "Video Generation Complete"
        return self.notify(
            event="video_complete",
            title=notif_title,
            message="Your video has been generated successfully and is ready for review.",
            data={"video_id": video_id},
        )

    def notify_job_failed(self, job_id: str, error: str) -> Notification:
        """Notify that a pipeline job has failed."""
        return self.notify(
            event="job_failed",
            title="Job Failed",
            message="A pipeline job encountered an error and could not complete.",
            data={"job_id": job_id, "error": error},
        )

    def notify_upload_complete(self, video_id: str, youtube_url: str) -> Notification:
        """Notify that a video has been uploaded to YouTube."""
        return self.notify(
            event="upload_complete",
            title="Video Uploaded to YouTube",
            message="Your video has been successfully uploaded and is now live.",
            data={"video_id": video_id, "youtube_url": youtube_url},
        )

    def notify_batch_complete(self, batch_id: str, results: dict) -> Notification:
        """Notify that a batch of videos has finished processing."""
        total = results.get("total", 0)
        succeeded = results.get("succeeded", 0)
        failed = results.get("failed", 0)
        return self.notify(
            event="batch_complete",
            title="Batch Processing Complete",
            message=(
                f"Batch {batch_id[:8]} finished: "
                f"{succeeded}/{total} succeeded, {failed} failed."
            ),
            data={
                "batch_id": batch_id,
                "total": total,
                "succeeded": succeeded,
                "failed": failed,
            },
        )

    def notify_cost_alert(self, current_cost: float, budget: float) -> Notification:
        """Notify when spending approaches or exceeds the budget."""
        pct = round((current_cost / budget) * 100, 1) if budget else 0
        if current_cost >= budget:
            severity = "exceeded"
            title = "Budget Exceeded"
        elif pct >= 90:
            severity = "critical"
            title = "Budget Alert: 90% Reached"
        elif pct >= 75:
            severity = "warning"
            title = "Budget Alert: 75% Reached"
        else:
            severity = "info"
            title = "Cost Update"

        return self.notify(
            event="cost_alert",
            title=title,
            message=(
                f"Current spending is ${current_cost:.2f} of your "
                f"${budget:.2f} budget ({pct}%)."
            ),
            data={
                "current_cost": current_cost,
                "budget": budget,
                "percentage": pct,
                "severity": severity,
            },
        )

    def notify_publish_complete(
        self,
        video_id: str,
        platforms: list[str],
        results: dict,
    ) -> Notification:
        """Notify that a video has been published to one or more platforms."""
        success_platforms = [p for p, r in results.items() if r.get("status") == "success"]
        failed_platforms = [p for p, r in results.items() if r.get("status") != "success"]

        if failed_platforms:
            title = "Publishing Partially Complete"
            message = (
                f"Published to {', '.join(success_platforms)}. "
                f"Failed on {', '.join(failed_platforms)}."
            )
        else:
            title = "Published Successfully"
            message = f"Video published to {', '.join(success_platforms)}."

        return self.notify(
            event="publish_complete",
            title=title,
            message=message,
            data={
                "video_id": video_id,
                "platforms": platforms,
                "results": results,
            },
        )

    def notify_schedule_fired(
        self,
        schedule_id: str,
        channel_name: str,
        topic: str,
    ) -> Notification:
        """Notify that a scheduled content generation has been triggered."""
        return self.notify(
            event="schedule_fired",
            title="Scheduled Generation Started",
            message=(
                f"Recurring schedule triggered for channel '{channel_name}'. "
                f"Topic: {topic}"
            ),
            data={
                "schedule_id": schedule_id,
                "channel_name": channel_name,
                "topic": topic,
            },
        )

    # ------------------------------------------------------------------
    # Database persistence
    # ------------------------------------------------------------------

    def _persist(
        self,
        event: str,
        title: str,
        message: str,
        data: dict | None,
        channels_sent: list[str],
    ) -> Notification:
        """Save the notification to the database."""
        session = get_session()
        try:
            notification = Notification(
                event=event,
                title=title,
                message=message,
                data_json=data,
                channels_sent=channels_sent,
            )
            session.add(notification)
            session.commit()
            session.refresh(notification)
            return notification
        except Exception:
            session.rollback()
            logger.error("Failed to persist notification", exc_info=True)
            # Return an unsaved notification so callers still get an object
            return Notification(
                event=event,
                title=title,
                message=message,
                data_json=data,
                channels_sent=channels_sent,
            )
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Query helpers (used by routes / API)
    # ------------------------------------------------------------------

    @staticmethod
    def get_unread_count() -> int:
        """Count unread notifications."""
        from sqlalchemy import func, select

        session = get_session()
        try:
            stmt = (
                select(func.count())
                .select_from(Notification)
                .where(Notification.read_at.is_(None))
            )
            return session.scalar(stmt) or 0
        finally:
            session.close()

    @staticmethod
    def get_recent(limit: int = 50, unread_only: bool = False) -> list[Notification]:
        """Fetch recent notifications, optionally filtered to unread."""
        from sqlalchemy import select

        session = get_session()
        try:
            stmt = select(Notification).order_by(Notification.created_at.desc()).limit(limit)
            if unread_only:
                stmt = stmt.where(Notification.read_at.is_(None))
            return list(session.scalars(stmt).all())
        finally:
            session.close()

    @staticmethod
    def mark_read(notification_id: str) -> bool:
        """Mark a single notification as read."""
        session = get_session()
        try:
            notification = session.get(Notification, notification_id)
            if notification and notification.read_at is None:
                notification.read_at = datetime.now(timezone.utc)
                session.commit()
                return True
            return False
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    @staticmethod
    def mark_all_read() -> int:
        """Mark all unread notifications as read. Returns count updated."""
        from sqlalchemy import update

        session = get_session()
        try:
            stmt = (
                update(Notification)
                .where(Notification.read_at.is_(None))
                .values(read_at=datetime.now(timezone.utc))
            )
            result = session.execute(stmt)
            session.commit()
            return result.rowcount  # type: ignore[return-value]
        except Exception:
            session.rollback()
            return 0
        finally:
            session.close()
