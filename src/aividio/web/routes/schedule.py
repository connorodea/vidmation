"""Scheduling routes — dashboard, CRUD, and HTMX endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from aividio.db.engine import get_session
from aividio.db.repos import ChannelRepo, VideoRepo
from aividio.models.video import VideoStatus
from aividio.scheduling.advanced import AdvancedScheduler
from aividio.web.templating import get_templates

router = APIRouter()


# ---------- Pages ----------


@router.get("/schedule", response_class=HTMLResponse)
async def schedule_dashboard(request: Request):
    """Schedule dashboard with calendar view, recurring cards, and timing suggestions."""
    templates = get_templates()
    scheduler = AdvancedScheduler()

    session = get_session()
    try:
        channel_repo = ChannelRepo(session)
        channels = channel_repo.list_all()

        video_repo = VideoRepo(session)
        ready_videos = video_repo.list_all(status=VideoStatus.READY, limit=50)

        all_schedules = scheduler.get_schedule(include_completed=False)
        one_time = [s for s in all_schedules if s["schedule_type"] == "one_time"]
        recurring = [s for s in all_schedules if s["schedule_type"] == "recurring"]

        # Get optimal times for first channel (if any)
        optimal_times: list[dict] = []
        if channels:
            optimal_times = scheduler.optimal_publish_times(channels[0].name)[:5]

        return templates.TemplateResponse(
            "schedule/dashboard.html",
            {
                "request": request,
                "one_time_schedules": one_time,
                "recurring_schedules": recurring,
                "channels": channels,
                "ready_videos": ready_videos,
                "optimal_times": optimal_times,
            },
        )
    finally:
        session.close()


# ---------- Actions ----------


@router.post("/schedule/video")
async def schedule_video(
    video_id: str = Form(...),
    publish_at: str = Form(...),
    platforms: list[str] = Form(["youtube"]),
):
    """Schedule a specific video for publishing."""
    try:
        publish_datetime = datetime.fromisoformat(publish_at).replace(tzinfo=timezone.utc)
    except ValueError:
        return RedirectResponse("/schedule?error=invalid_date", status_code=303)

    scheduler = AdvancedScheduler()
    try:
        scheduler.schedule_video(
            video_id=video_id,
            publish_at=publish_datetime,
            platforms=platforms,
        )
    except ValueError as exc:
        return RedirectResponse(f"/schedule?error={exc}", status_code=303)

    return RedirectResponse("/schedule?success=scheduled", status_code=303)


@router.post("/schedule/recurring")
async def schedule_recurring(
    channel_id: str = Form(...),
    cron_expression: str = Form(...),
    topic_source: str = Form("ai"),
    platforms: list[str] = Form(["youtube"]),
    rss_url: str = Form(""),
):
    """Set up a recurring video generation schedule."""
    session = get_session()
    try:
        channel_repo = ChannelRepo(session)
        channel = channel_repo.get(channel_id)
        if not channel:
            return RedirectResponse("/schedule?error=channel_not_found", status_code=303)

        topic_config: dict = {}
        if topic_source == "rss" and rss_url:
            topic_config["feed_url"] = rss_url

        scheduler = AdvancedScheduler()
        scheduler.schedule_recurring(
            channel_name=channel.name,
            cron_expression=cron_expression,
            topic_source=topic_source,
            topic_config=topic_config,
            platforms=platforms,
        )
    except ValueError as exc:
        return RedirectResponse(f"/schedule?error={exc}", status_code=303)
    finally:
        session.close()

    return RedirectResponse("/schedule?success=recurring_created", status_code=303)


@router.post("/schedule/{schedule_id}/pause")
async def pause_schedule(schedule_id: str):
    """Pause an active schedule."""
    scheduler = AdvancedScheduler()
    scheduler.pause_schedule(schedule_id)
    return RedirectResponse("/schedule", status_code=303)


@router.post("/schedule/{schedule_id}/resume")
async def resume_schedule(schedule_id: str):
    """Resume a paused schedule."""
    scheduler = AdvancedScheduler()
    scheduler.resume_schedule(schedule_id)
    return RedirectResponse("/schedule", status_code=303)


@router.delete("/schedule/{schedule_id}")
async def delete_schedule(schedule_id: str):
    """Delete a schedule."""
    scheduler = AdvancedScheduler()
    deleted = scheduler.delete_schedule(schedule_id)
    if deleted:
        return JSONResponse({"status": "deleted"})
    return JSONResponse({"error": "Schedule not found"}, status_code=404)


# ---------- HTMX / API ----------


@router.get("/api/schedule/upcoming", response_class=HTMLResponse)
async def api_schedule_upcoming(request: Request, channel: str | None = None):
    """HTMX partial — render upcoming schedule items."""
    templates = get_templates()
    scheduler = AdvancedScheduler()
    schedules = scheduler.get_schedule(channel_name=channel)

    # Return just the schedule list fragment
    html_parts: list[str] = []
    for s in schedules[:20]:
        status_class = {
            "active": "text-green-400 bg-green-500/10",
            "paused": "text-yellow-400 bg-yellow-500/10",
            "completed": "text-gray-500 bg-gray-500/10",
            "failed": "text-red-400 bg-red-500/10",
        }.get(s["status"], "text-gray-400 bg-gray-500/10")

        type_label = "One-time" if s["schedule_type"] == "one_time" else "Recurring"
        next_run = s.get("next_run_at", "—")
        platforms = ", ".join(s.get("platforms", []))

        html_parts.append(f"""
        <div class="flex items-center justify-between p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:border-white/[0.1] transition-colors">
            <div class="flex items-center gap-4">
                <span class="inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium {status_class}">
                    {s["status"].title()}
                </span>
                <div>
                    <p class="text-sm font-medium text-white">{type_label}</p>
                    <p class="text-xs text-gray-500">Next: {next_run} &bull; {platforms}</p>
                </div>
            </div>
            <div class="flex items-center gap-2">
                {f'<form method="post" action="/schedule/{s["id"]}/pause"><button class="text-xs text-gray-500 hover:text-yellow-400">Pause</button></form>' if s["status"] == "active" else ""}
                {f'<form method="post" action="/schedule/{s["id"]}/resume"><button class="text-xs text-gray-500 hover:text-green-400">Resume</button></form>' if s["status"] == "paused" else ""}
                <button hx-delete="/schedule/{s["id"]}" hx-confirm="Delete this schedule?" hx-target="closest div" hx-swap="outerHTML" class="text-xs text-gray-500 hover:text-red-400">Delete</button>
            </div>
        </div>
        """)

    if not html_parts:
        html_parts.append(
            '<div class="py-8 text-center text-gray-500 text-sm">No upcoming schedules</div>'
        )

    return HTMLResponse("\n".join(html_parts))
