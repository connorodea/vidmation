"""Notification routes — notification centre, mark-read, and badge count."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from aividio.notifications.manager import NotificationManager
from aividio.web.templating import get_templates

router = APIRouter()


# ---------- Pages ----------


@router.get("/notifications", response_class=HTMLResponse)
async def notification_center(
    request: Request,
    filter: str | None = None,
):
    """Notification centre page with filterable list."""
    templates = get_templates()
    manager = NotificationManager()

    unread_only = filter == "unread"
    notifications = manager.get_recent(limit=100, unread_only=unread_only)
    unread_count = manager.get_unread_count()

    # Get unique event types for filter dropdown
    event_types = sorted(set(n.event for n in notifications))

    # Apply event-type filter if specified and not 'unread'
    if filter and filter not in ("unread", "all", None):
        notifications = [n for n in notifications if n.event == filter]

    return templates.TemplateResponse(
        "notifications/center.html",
        {
            "request": request,
            "notifications": notifications,
            "unread_count": unread_count,
            "current_filter": filter,
            "event_types": event_types,
        },
    )


# ---------- API ----------


@router.post("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    """Mark a single notification as read."""
    success = NotificationManager.mark_read(notification_id)
    if success:
        unread = NotificationManager.get_unread_count()
        return JSONResponse({
            "status": "ok",
            "unread_count": unread,
        })
    return JSONResponse({"error": "Notification not found or already read"}, status_code=404)


@router.post("/api/notifications/read-all")
async def mark_all_read():
    """Mark all notifications as read."""
    count = NotificationManager.mark_all_read()
    return JSONResponse({"status": "ok", "marked_count": count})


@router.get("/api/notifications/unread-count")
async def unread_count():
    """Get the count of unread notifications (for header badge via HTMX polling)."""
    count = NotificationManager.get_unread_count()
    return JSONResponse({"unread_count": count})


@router.get("/api/notifications/badge", response_class=HTMLResponse)
async def notification_badge():
    """HTMX partial — returns the notification badge HTML fragment.

    Used for polling the notification dot in the header.
    """
    count = NotificationManager.get_unread_count()
    if count > 0:
        display = str(count) if count < 100 else "99+"
        return HTMLResponse(
            f'<span class="absolute -top-0.5 -right-0.5 flex items-center justify-center '
            f'min-w-[18px] h-[18px] rounded-full bg-brand-500 text-[10px] font-bold text-white '
            f'ring-2 ring-gray-950 px-1">{display}</span>'
        )
    return HTMLResponse("")
