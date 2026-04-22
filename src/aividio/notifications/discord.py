"""Discord webhook notifier — sends embed-formatted messages.

Configuration:
    VIDMATION_DISCORD_WEBHOOK_URL: full Discord webhook URL
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("aividio.notifications.discord")

# Event-to-colour mapping (Discord embed colour is an integer).
_EVENT_COLOURS: dict[str, int] = {
    "video_complete": 0x22C55E,   # green
    "job_failed": 0xEF4444,       # red
    "upload_complete": 0x6366F1,  # brand indigo
    "batch_complete": 0x3B82F6,   # blue
    "cost_alert": 0xEAB308,       # yellow
    "schedule_fired": 0x8B5CF6,   # purple
    "publish_complete": 0x14B8A6, # teal
}

_EVENT_EMOJIS: dict[str, str] = {
    "video_complete": ":movie_camera:",
    "job_failed": ":warning:",
    "upload_complete": ":outbox_tray:",
    "batch_complete": ":package:",
    "cost_alert": ":moneybag:",
    "schedule_fired": ":alarm_clock:",
    "publish_complete": ":rocket:",
}


class DiscordNotifier:
    """Send notifications to a Discord channel via webhook.

    Messages are formatted as rich embeds with colour-coded event types,
    optional fields for metadata, and a footer showing the event source.
    """

    def __init__(self) -> None:
        self.webhook_url = os.getenv("VIDMATION_DISCORD_WEBHOOK_URL", "")

    @property
    def is_configured(self) -> bool:
        return bool(self.webhook_url)

    def send(
        self,
        event: str,
        title: str,
        message: str,
        data: dict | None = None,
    ) -> bool:
        """Send a Discord embed notification.

        Returns True on success, False on failure.
        """
        if not self.is_configured:
            logger.debug("Discord notifier not configured, skipping")
            return False

        embed = self._build_embed(event, title, message, data)
        payload: dict[str, Any] = {
            "username": "VIDMATION",
            "avatar_url": "https://aividio.io/static/images/logo.png",
            "embeds": [embed],
        }

        try:
            import httpx

            response = httpx.post(
                self.webhook_url,
                json=payload,
                timeout=10.0,
            )
            if response.status_code in (200, 204):
                logger.info("Discord notification sent: %s", event)
                return True

            logger.error(
                "Discord webhook error %d: %s",
                response.status_code,
                response.text[:500],
            )
            return False
        except Exception:
            logger.error("Failed to send Discord notification", exc_info=True)
            return False

    def _build_embed(
        self,
        event: str,
        title: str,
        message: str,
        data: dict | None = None,
    ) -> dict[str, Any]:
        """Build a Discord embed object."""
        emoji = _EVENT_EMOJIS.get(event, ":bell:")
        colour = _EVENT_COLOURS.get(event, 0x6366F1)

        embed: dict[str, Any] = {
            "title": f"{emoji}  {title}",
            "description": message,
            "color": colour,
            "footer": {
                "text": f"VIDMATION | Event: {event}",
            },
        }

        # Add data fields
        fields: list[dict[str, Any]] = []
        if data:
            if "video_id" in data:
                fields.append({
                    "name": "Video ID",
                    "value": f"`{data['video_id']}`",
                    "inline": True,
                })
            if "job_id" in data:
                fields.append({
                    "name": "Job ID",
                    "value": f"`{data['job_id']}`",
                    "inline": True,
                })
            if "youtube_url" in data:
                fields.append({
                    "name": "YouTube",
                    "value": f"[Watch Video]({data['youtube_url']})",
                    "inline": False,
                })
            if "error" in data:
                error_text = str(data["error"])[:1000]
                fields.append({
                    "name": "Error Details",
                    "value": f"```\n{error_text}\n```",
                    "inline": False,
                })
            if "current_cost" in data and "budget" in data:
                pct = round((data["current_cost"] / data["budget"]) * 100, 1) if data["budget"] else 0
                fields.append({
                    "name": "Current Spend",
                    "value": f"${data['current_cost']:.2f}",
                    "inline": True,
                })
                fields.append({
                    "name": "Budget",
                    "value": f"${data['budget']:.2f}",
                    "inline": True,
                })
                fields.append({
                    "name": "Usage",
                    "value": f"{pct}%",
                    "inline": True,
                })
            if "platforms" in data:
                platforms_str = ", ".join(str(p) for p in data["platforms"])
                fields.append({
                    "name": "Platforms",
                    "value": platforms_str,
                    "inline": True,
                })
            # Batch results
            if "total" in data and "succeeded" in data:
                fields.append({
                    "name": "Results",
                    "value": (
                        f"Total: {data['total']}  |  "
                        f"Succeeded: {data['succeeded']}  |  "
                        f"Failed: {data.get('failed', 0)}"
                    ),
                    "inline": False,
                })

        if fields:
            embed["fields"] = fields

        return embed
