"""Webhook system — register endpoints and fire events with signed payloads."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from aividio.db.engine import get_session
from aividio.models.webhook import Webhook

logger = logging.getLogger(__name__)

# Maximum retries with exponential backoff
_MAX_RETRIES = 3
_BASE_BACKOFF_SECONDS = 1.0  # 1s, 2s, 4s

EVENTS = [
    "video.created",
    "video.completed",
    "video.failed",
    "video.uploaded",
    "job.started",
    "job.completed",
    "job.failed",
    "batch.completed",
]


def _sign_payload(payload_bytes: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for a payload."""
    return hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


class WebhookManager:
    """Send webhook notifications on events."""

    EVENTS = EVENTS

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    @property
    def session(self) -> Session:
        if self._session is None:
            self._session = get_session()
        return self._session

    # -- Registration -------------------------------------------------------

    def register(
        self,
        url: str,
        events: list[str],
        secret: str | None = None,
        description: str = "",
    ) -> dict:
        """Register a webhook endpoint.

        Args:
            url: HTTPS URL that will receive POST requests.
            events: Event types to subscribe to.
            secret: Optional HMAC-SHA256 signing secret.
            description: Human-readable note.

        Returns:
            Dict representation of the created webhook.
        """
        # Validate event names
        invalid = set(events) - set(self.EVENTS)
        if invalid:
            raise ValueError(
                f"Invalid event types: {invalid}. Valid events: {self.EVENTS}"
            )

        webhook = Webhook(
            url=url,
            events=events,
            secret=secret,
            description=description,
        )
        self.session.add(webhook)
        self.session.commit()
        self.session.refresh(webhook)
        logger.info("Registered webhook %s -> %s for events %s", webhook.id[:8], url, events)
        return self._to_dict(webhook)

    # -- Firing -------------------------------------------------------------

    async def fire(self, event: str, payload: dict) -> None:
        """Fire webhook to all registered endpoints for this event.

        Delivers asynchronously with retries and exponential backoff.
        Signs payload with HMAC-SHA256 if the webhook has a secret configured.
        """
        webhooks = self._get_active_for_event(event)
        if not webhooks:
            return

        delivery_id = str(uuid.uuid4())
        body = json.dumps(
            {
                "event": event,
                "delivery_id": delivery_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": payload,
            },
            default=str,
        )
        body_bytes = body.encode()

        tasks = [self._deliver(wh, body, body_bytes) for wh in webhooks]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _deliver(self, webhook: Webhook, body: str, body_bytes: bytes) -> None:
        """Deliver a single webhook with retry logic."""
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": "AIVIDIO-Webhooks/1.0",
        }
        if webhook.secret:
            sig = _sign_payload(body_bytes, webhook.secret)
            headers["X-Vidmation-Signature"] = f"sha256={sig}"

        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(webhook.url, content=body, headers=headers)
                    resp.raise_for_status()

                # Success — reset failure counter
                self._mark_success(webhook.id)
                logger.info(
                    "Webhook %s delivered to %s (status %s)",
                    webhook.id[:8],
                    webhook.url,
                    resp.status_code,
                )
                return

            except Exception as exc:
                last_error = exc
                backoff = _BASE_BACKOFF_SECONDS * (2 ** attempt)
                logger.warning(
                    "Webhook %s delivery attempt %d/%d to %s failed: %s (retrying in %.1fs)",
                    webhook.id[:8],
                    attempt + 1,
                    _MAX_RETRIES,
                    webhook.url,
                    exc,
                    backoff,
                )
                await asyncio.sleep(backoff)

        # All retries exhausted
        self._mark_failure(webhook.id)
        logger.error(
            "Webhook %s delivery to %s FAILED after %d attempts: %s",
            webhook.id[:8],
            webhook.url,
            _MAX_RETRIES,
            last_error,
        )

    def fire_sync(self, event: str, payload: dict) -> None:
        """Synchronous convenience wrapper — fires in a background task.

        Safe to call from synchronous code; spins up an event loop if needed.
        """
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.fire(event, payload))
        except RuntimeError:
            asyncio.run(self.fire(event, payload))

    # -- Test ---------------------------------------------------------------

    def test_webhook(self, webhook_id: str) -> dict:
        """Send a test event to a webhook endpoint and return the result."""
        webhook = self.session.get(Webhook, webhook_id)
        if webhook is None:
            raise ValueError(f"Webhook '{webhook_id}' not found")

        body = json.dumps(
            {
                "event": "webhook.test",
                "delivery_id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {"message": "This is a test delivery from AIVIDIO."},
            },
            default=str,
        )
        body_bytes = body.encode()

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": "AIVIDIO-Webhooks/1.0",
        }
        if webhook.secret:
            sig = _sign_payload(body_bytes, webhook.secret)
            headers["X-Vidmation-Signature"] = f"sha256={sig}"

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(webhook.url, content=body, headers=headers)
            return {
                "webhook_id": webhook_id,
                "status": "delivered",
                "response_code": resp.status_code,
                "response_body": resp.text[:500],
                "error": None,
            }
        except Exception as exc:
            return {
                "webhook_id": webhook_id,
                "status": "failed",
                "response_code": None,
                "response_body": None,
                "error": str(exc),
            }

    # -- Listing / deletion -------------------------------------------------

    def list_webhooks(self, active_only: bool = False) -> list[dict]:
        """Return all webhooks as dicts."""
        stmt = select(Webhook).order_by(Webhook.created_at.desc())
        if active_only:
            stmt = stmt.where(Webhook.is_active.is_(True))
        return [self._to_dict(wh) for wh in self.session.scalars(stmt).all()]

    def get(self, webhook_id: str) -> Webhook | None:
        return self.session.get(Webhook, webhook_id)

    def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook by ID."""
        webhook = self.session.get(Webhook, webhook_id)
        if webhook is None:
            return False
        self.session.delete(webhook)
        self.session.commit()
        logger.info("Deleted webhook %s (%s)", webhook_id[:8], webhook.url)
        return True

    # -- Internal helpers ---------------------------------------------------

    def _get_active_for_event(self, event: str) -> list[Webhook]:
        """Get all active webhooks subscribed to the given event."""
        stmt = select(Webhook).where(Webhook.is_active.is_(True))
        all_active = list(self.session.scalars(stmt).all())
        return [wh for wh in all_active if event in (wh.events or [])]

    def _mark_success(self, webhook_id: str) -> None:
        session = get_session()
        try:
            wh = session.get(Webhook, webhook_id)
            if wh:
                wh.last_triggered_at = datetime.now(timezone.utc)
                wh.failure_count = 0
                session.commit()
        finally:
            session.close()

    def _mark_failure(self, webhook_id: str) -> None:
        session = get_session()
        try:
            wh = session.get(Webhook, webhook_id)
            if wh:
                wh.failure_count = (wh.failure_count or 0) + 1
                wh.last_triggered_at = datetime.now(timezone.utc)
                # Disable after 10 consecutive failures
                if wh.failure_count >= 10:
                    wh.is_active = False
                    logger.warning(
                        "Webhook %s disabled after %d consecutive failures",
                        webhook_id[:8],
                        wh.failure_count,
                    )
                session.commit()
        finally:
            session.close()

    @staticmethod
    def _to_dict(webhook: Webhook) -> dict:
        return {
            "id": webhook.id,
            "url": webhook.url,
            "events": webhook.events or [],
            "is_active": webhook.is_active,
            "description": webhook.description,
            "failure_count": webhook.failure_count,
            "last_triggered_at": webhook.last_triggered_at,
            "created_at": webhook.created_at,
            "updated_at": webhook.updated_at,
        }
