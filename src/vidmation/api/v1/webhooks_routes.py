"""Webhook management API — register, list, delete, and test webhooks.

All endpoints require JWT authentication.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from vidmation.api.v1.schemas import (
    ErrorResponse,
    WebhookCreateRequest,
    WebhookResponse,
    WebhookTestResponse,
)
from vidmation.api.webhooks import WebhookManager
from vidmation.auth.dependencies import require_active_user
from vidmation.db.engine import get_session
from vidmation.models.user import User

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# ---------------------------------------------------------------------------
# POST /webhooks — register a new webhook
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}},
)
async def register_webhook(
    body: WebhookCreateRequest,
    user: User = Depends(require_active_user),
):
    """Register a new webhook endpoint to receive event notifications."""
    session = get_session()
    try:
        mgr = WebhookManager(session)
        try:
            result = mgr.register(
                url=body.url,
                events=body.events,
                secret=body.secret,
                description=body.description,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            )

        return WebhookResponse(**result)

    finally:
        session.close()


# ---------------------------------------------------------------------------
# GET /webhooks — list registered webhooks
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=list[WebhookResponse],
)
async def list_webhooks(
    user: User = Depends(require_active_user),
):
    """List all registered webhooks."""
    session = get_session()
    try:
        mgr = WebhookManager(session)
        webhooks = mgr.list_webhooks()
        return [WebhookResponse(**wh) for wh in webhooks]
    finally:
        session.close()


# ---------------------------------------------------------------------------
# DELETE /webhooks/{id} — delete a webhook
# ---------------------------------------------------------------------------


@router.delete(
    "/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}},
)
async def delete_webhook(
    webhook_id: str,
    user: User = Depends(require_active_user),
):
    """Delete a registered webhook."""
    session = get_session()
    try:
        mgr = WebhookManager(session)
        if not mgr.delete_webhook(webhook_id):
            raise HTTPException(status_code=404, detail="Webhook not found")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# POST /webhooks/{id}/test — send a test event
# ---------------------------------------------------------------------------


@router.post(
    "/{webhook_id}/test",
    response_model=WebhookTestResponse,
    responses={404: {"model": ErrorResponse}},
)
async def test_webhook(
    webhook_id: str,
    user: User = Depends(require_active_user),
):
    """Send a test event to a webhook endpoint to verify connectivity."""
    session = get_session()
    try:
        mgr = WebhookManager(session)
        webhook = mgr.get(webhook_id)
        if webhook is None:
            raise HTTPException(status_code=404, detail="Webhook not found")

        result = mgr.test_webhook(webhook_id)
        return WebhookTestResponse(**result)
    finally:
        session.close()
