"""Multi-channel notification system for VIDMATION.

Supports email (Resend/SMTP), Discord webhooks, Slack webhooks,
and in-app notifications stored in the database.
"""

from aividio.notifications.manager import NotificationManager

__all__ = ["NotificationManager"]
