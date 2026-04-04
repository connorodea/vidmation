"""Slack webhook notifier — sends Block Kit formatted messages.

Configuration:
    VIDMATION_SLACK_WEBHOOK_URL: full Slack incoming webhook URL
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("vidmation.notifications.slack")

_EVENT_EMOJIS: dict[str, str] = {
    "video_complete": ":movie_camera:",
    "job_failed": ":rotating_light:",
    "upload_complete": ":outbox_tray:",
    "batch_complete": ":package:",
    "cost_alert": ":money_with_wings:",
    "schedule_fired": ":alarm_clock:",
    "publish_complete": ":rocket:",
}

_EVENT_COLOURS: dict[str, str] = {
    "video_complete": "#22c55e",
    "job_failed": "#ef4444",
    "upload_complete": "#6366f1",
    "batch_complete": "#3b82f6",
    "cost_alert": "#eab308",
    "schedule_fired": "#8b5cf6",
    "publish_complete": "#14b8a6",
}


class SlackNotifier:
    """Send notifications to a Slack channel via incoming webhook.

    Messages are formatted using Slack's Block Kit for rich display,
    with colour-coded attachments per event type.
    """

    def __init__(self) -> None:
        self.webhook_url = os.getenv("VIDMATION_SLACK_WEBHOOK_URL", "")

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
        """Send a Slack Block Kit notification.

        Returns True on success, False on failure.
        """
        if not self.is_configured:
            logger.debug("Slack notifier not configured, skipping")
            return False

        payload = self._build_payload(event, title, message, data)

        try:
            import httpx

            response = httpx.post(
                self.webhook_url,
                json=payload,
                timeout=10.0,
            )
            if response.status_code == 200 and response.text == "ok":
                logger.info("Slack notification sent: %s", event)
                return True

            logger.error(
                "Slack webhook error %d: %s",
                response.status_code,
                response.text[:500],
            )
            return False
        except Exception:
            logger.error("Failed to send Slack notification", exc_info=True)
            return False

    def _build_payload(
        self,
        event: str,
        title: str,
        message: str,
        data: dict | None = None,
    ) -> dict[str, Any]:
        """Build a Slack Block Kit payload with attachments."""
        emoji = _EVENT_EMOJIS.get(event, ":bell:")
        colour = _EVENT_COLOURS.get(event, "#6366f1")

        blocks: list[dict[str, Any]] = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji}  {title}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message,
                },
            },
        ]

        # Build context fields from data
        fields: list[dict[str, Any]] = []
        if data:
            if "video_id" in data:
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*Video ID:*\n`{data['video_id']}`",
                })
            if "job_id" in data:
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*Job ID:*\n`{data['job_id']}`",
                })
            if "youtube_url" in data:
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*YouTube:*\n<{data['youtube_url']}|Watch Video>",
                })
            if "current_cost" in data and "budget" in data:
                pct = round((data["current_cost"] / data["budget"]) * 100, 1) if data["budget"] else 0
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*Spend:* ${data['current_cost']:.2f} / ${data['budget']:.2f} ({pct}%)",
                })
            if "error" in data:
                error_text = str(data["error"])[:500]
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Error:*\n```{error_text}```",
                    },
                })
            if "total" in data and "succeeded" in data:
                fields.append({
                    "type": "mrkdwn",
                    "text": (
                        f"*Results:* {data['succeeded']}/{data['total']} succeeded, "
                        f"{data.get('failed', 0)} failed"
                    ),
                })
            if "platforms" in data:
                platforms_str = ", ".join(str(p) for p in data["platforms"])
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*Platforms:* {platforms_str}",
                })

        if fields:
            blocks.append({
                "type": "section",
                "fields": fields[:10],  # Slack limits to 10 fields per section
            })

        # Add divider and footer context
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f":zap: *VIDMATION* | Event: `{event}`",
                }
            ],
        })

        return {
            "attachments": [
                {
                    "color": colour,
                    "blocks": blocks,
                }
            ],
        }
