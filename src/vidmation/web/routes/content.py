"""Content planning routes — calendar, series, and topic suggestions."""

from __future__ import annotations

import json
from datetime import date, datetime

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from vidmation.content.calendar import ContentCalendar
from vidmation.content.planner import ContentPlanner
from vidmation.content.series import SeriesManager
from vidmation.config.settings import get_settings
from vidmation.db.engine import get_session
from vidmation.db.repos import ChannelRepo
from vidmation.queue.tasks import enqueue_video
from vidmation.web.templating import get_templates

router = APIRouter()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_channels() -> list:
    session = get_session()
    try:
        return ChannelRepo(session).list_all()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Content Calendar
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def content_calendar_page(
    request: Request,
    calendar_id: str | None = None,
    view: str = "weekly",
):
    """Content calendar view — weekly or monthly grid."""
    templates = get_templates()
    channels = _get_channels()

    calendars = ContentCalendar.list_calendars()
    active_calendar: ContentCalendar | None = None
    entries: list[dict] = []
    stats: dict = {}

    if calendar_id:
        try:
            active_calendar = ContentCalendar.load(calendar_id)
            entries = active_calendar.entries
            stats = active_calendar.get_stats()
        except FileNotFoundError:
            pass
    elif calendars:
        # Default to the most recent calendar
        latest = calendars[-1]
        try:
            active_calendar = ContentCalendar.load(latest["id"])
            entries = active_calendar.entries
            stats = active_calendar.get_stats()
            calendar_id = latest["id"]
        except FileNotFoundError:
            pass

    # Group entries by week for the weekly view
    weeks: dict[str, list[dict]] = {}
    for entry in entries:
        try:
            entry_date = datetime.strptime(entry["date"], "%Y-%m-%d").date()
            iso_year, iso_week, _ = entry_date.isocalendar()
            week_key = f"{iso_year}-W{iso_week:02d}"
        except (KeyError, ValueError):
            week_key = "unscheduled"
        weeks.setdefault(week_key, []).append(entry)

    return templates.TemplateResponse(
        "content/calendar.html",
        {
            "request": request,
            "calendars": calendars,
            "active_calendar_id": calendar_id,
            "entries": entries,
            "weeks": dict(sorted(weeks.items())),
            "stats": stats,
            "channels": channels,
            "view": view,
            "today": date.today().isoformat(),
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def content_new_page(request: Request):
    """Form to generate a new content calendar."""
    templates = get_templates()
    channels = _get_channels()
    return templates.TemplateResponse(
        "content/calendar.html",
        {
            "request": request,
            "calendars": ContentCalendar.list_calendars(),
            "active_calendar_id": None,
            "entries": [],
            "weeks": {},
            "stats": {},
            "channels": channels,
            "view": "weekly",
            "today": date.today().isoformat(),
            "show_generate_form": True,
        },
    )


@router.post("/generate")
async def content_generate(
    channel_name: str = Form("default"),
    weeks: int = Form(4),
    videos_per_week: int = Form(3),
):
    """Generate a new content calendar using AI."""
    settings = get_settings()
    planner = ContentPlanner(settings=settings)

    entries = planner.generate_content_calendar(
        channel_name=channel_name,
        weeks=weeks,
        videos_per_week=videos_per_week,
    )

    # Persist to a new calendar
    calendar = ContentCalendar()
    calendar.channel_name = channel_name
    calendar.add_entries(entries)
    calendar.save()

    return RedirectResponse(
        f"/content?calendar_id={calendar.calendar_id}",
        status_code=303,
    )


@router.post("/entry/{entry_id}/status")
async def content_entry_status(
    entry_id: str,
    calendar_id: str = Form(...),
    status: str = Form(...),
):
    """Update a calendar entry's status (HTMX)."""
    try:
        calendar = ContentCalendar.load(calendar_id)
    except FileNotFoundError:
        return Response("Calendar not found", status_code=404)

    calendar.mark_status(entry_id, status)
    calendar.save()

    return RedirectResponse(
        f"/content?calendar_id={calendar_id}",
        status_code=303,
    )


@router.post("/entry/{entry_id}/generate")
async def content_entry_generate(
    entry_id: str,
    calendar_id: str = Form(...),
):
    """Generate a video from a calendar entry."""
    try:
        calendar = ContentCalendar.load(calendar_id)
    except FileNotFoundError:
        return Response("Calendar not found", status_code=404)

    entry = calendar.get_entry(entry_id)
    if not entry:
        return Response("Entry not found", status_code=404)

    topic = entry.get("topic", entry.get("title", "Untitled"))
    channel_name = calendar.channel_name or "default"

    try:
        video, job = enqueue_video(topic=topic, channel_name=channel_name)
        calendar.mark_completed(entry_id, video_id=video.id)
        calendar.save()
        return RedirectResponse(f"/videos/{video.id}", status_code=303)
    except ValueError as exc:
        return Response(f"Error: {exc}", status_code=400)


@router.post("/entry/{entry_id}/reschedule")
async def content_entry_reschedule(
    entry_id: str,
    calendar_id: str = Form(...),
    new_date: str = Form(...),
):
    """Reschedule a calendar entry to a new date (HTMX / Alpine.js)."""
    try:
        calendar = ContentCalendar.load(calendar_id)
    except FileNotFoundError:
        return Response("Calendar not found", status_code=404)

    # Validate date format
    try:
        datetime.strptime(new_date, "%Y-%m-%d")
    except ValueError:
        return Response("Invalid date format (expected YYYY-MM-DD)", status_code=400)

    calendar.update_entry(entry_id, {"date": new_date})
    calendar.save()

    return RedirectResponse(
        f"/content?calendar_id={calendar_id}",
        status_code=303,
    )


@router.get("/export/{calendar_id}.ics")
async def content_export_ical(calendar_id: str):
    """Export a calendar as iCal file."""
    try:
        calendar = ContentCalendar.load(calendar_id)
    except FileNotFoundError:
        return Response("Calendar not found", status_code=404)

    ical = calendar.export_ical()
    return Response(
        content=ical,
        media_type="text/calendar",
        headers={
            "Content-Disposition": f"attachment; filename=vidmation-calendar-{calendar_id[:8]}.ics"
        },
    )


@router.post("/{calendar_id}/enqueue-due")
async def content_enqueue_due(calendar_id: str):
    """Auto-enqueue all pending entries that are due today or earlier."""
    try:
        calendar = ContentCalendar.load(calendar_id)
    except FileNotFoundError:
        return Response("Calendar not found", status_code=404)

    due_entries = calendar.enqueue_pending()
    channel_name = calendar.channel_name or "default"

    enqueued = 0
    for entry in due_entries:
        topic = entry.get("topic", entry.get("title", "Untitled"))
        try:
            video, job = enqueue_video(topic=topic, channel_name=channel_name)
            calendar.mark_completed(entry["id"], video_id=video.id)
            enqueued += 1
        except ValueError:
            calendar.mark_status(entry["id"], "pending")

    calendar.save()
    return RedirectResponse(
        f"/content?calendar_id={calendar_id}",
        status_code=303,
    )


# ---------------------------------------------------------------------------
# Series Management
# ---------------------------------------------------------------------------

@router.get("/series", response_class=HTMLResponse)
async def series_list_page(
    request: Request,
    channel_name: str | None = None,
):
    """Series management page."""
    templates = get_templates()
    manager = SeriesManager()
    series_list = manager.list_series(channel_name=channel_name)
    channels = _get_channels()

    return templates.TemplateResponse(
        "content/series.html",
        {
            "request": request,
            "series_list": series_list,
            "channels": channels,
            "channel_filter": channel_name,
        },
    )


@router.get("/series/{series_id}", response_class=HTMLResponse)
async def series_detail_page(request: Request, series_id: str):
    """Series detail view with episodes."""
    templates = get_templates()
    manager = SeriesManager()

    try:
        series = manager.get_series(series_id)
    except FileNotFoundError:
        return HTMLResponse("Series not found", status_code=404)

    next_episode = manager.get_next_episode(series_id)

    return templates.TemplateResponse(
        "content/series.html",
        {
            "request": request,
            "series_list": manager.list_series(),
            "channels": _get_channels(),
            "channel_filter": None,
            "active_series": series,
            "next_episode": next_episode,
        },
    )


@router.post("/series/create")
async def series_create(
    name: str = Form(...),
    description: str = Form(""),
    channel_name: str = Form("default"),
    episodes_text: str = Form(""),
):
    """Create a new series."""
    manager = SeriesManager()
    episode_topics = [
        line.strip()
        for line in episodes_text.strip().splitlines()
        if line.strip()
    ]

    series = manager.create_series(
        name=name,
        description=description,
        channel_name=channel_name,
        episode_topics=episode_topics or None,
    )

    return RedirectResponse(f"/content/series/{series['id']}", status_code=303)


@router.post("/series/{series_id}/episode")
async def series_add_episode(
    series_id: str,
    topic: str = Form(...),
    title: str = Form(""),
):
    """Add an episode to a series."""
    manager = SeriesManager()
    manager.add_episode(series_id=series_id, topic=topic, title=title)
    return RedirectResponse(f"/content/series/{series_id}", status_code=303)


@router.post("/series/{series_id}/episode/{episode_id}/generate")
async def series_generate_episode(series_id: str, episode_id: str):
    """Generate a video for a series episode."""
    manager = SeriesManager()
    try:
        series = manager.get_series(series_id)
    except FileNotFoundError:
        return Response("Series not found", status_code=404)

    context = manager.get_episode_context(series_id, episode_id)
    current = context.get("current_episode")
    if not current:
        return Response("Episode not found", status_code=404)

    topic = (
        f"{series['name']} - {current.get('title', current.get('topic', 'Untitled'))}"
    )
    channel_name = series.get("channel_name", "default")

    try:
        video, job = enqueue_video(topic=topic, channel_name=channel_name)
        manager.mark_episode_completed(
            series_id=series_id,
            episode_id=episode_id,
            video_id=video.id,
        )
        return RedirectResponse(f"/videos/{video.id}", status_code=303)
    except ValueError as exc:
        return Response(f"Error: {exc}", status_code=400)


@router.post("/series/{series_id}/delete")
async def series_delete(series_id: str):
    """Delete a series."""
    manager = SeriesManager()
    manager.delete_series(series_id)
    return RedirectResponse("/content/series", status_code=303)


# ---------------------------------------------------------------------------
# API / HTMX Endpoints
# ---------------------------------------------------------------------------

@router.get("/api/content/suggestions", response_class=HTMLResponse)
async def api_content_suggestions(
    request: Request,
    niche: str = Query("general"),
    count: int = Query(10, ge=1, le=30),
):
    """HTMX endpoint — returns HTML fragment with topic suggestions."""
    settings = get_settings()
    planner = ContentPlanner(settings=settings)
    topics = planner.trending_topics(niche=niche, count=count)

    # Return a simple HTML table fragment for HTMX swap
    rows = []
    for t in topics:
        score = t.get("relevance_score", 0)
        score_color = (
            "text-green-400" if score >= 0.7
            else "text-yellow-400" if score >= 0.4
            else "text-gray-400"
        )
        competition = t.get("competition", "unknown")
        comp_color = {
            "low": "bg-green-900/50 text-green-400",
            "medium": "bg-yellow-900/50 text-yellow-400",
            "high": "bg-red-900/50 text-red-400",
        }.get(competition, "bg-gray-800 text-gray-400")

        rows.append(f"""
        <tr class="hover:bg-gray-900/50">
            <td class="px-4 py-3 font-medium">{t.get('topic', '')}</td>
            <td class="px-4 py-3 {score_color}">{score:.0%}</td>
            <td class="px-4 py-3">
                <span class="px-2 py-0.5 rounded text-xs {comp_color}">{competition}</span>
            </td>
            <td class="px-4 py-3 text-gray-400">{t.get('timeliness', '')}</td>
            <td class="px-4 py-3 text-gray-500 text-xs">{t.get('suggested_title', '')}</td>
        </tr>
        """)

    html = f"""
    <table class="w-full text-sm">
        <thead class="bg-gray-900">
            <tr>
                <th class="px-4 py-3 text-left text-gray-400 font-medium">Topic</th>
                <th class="px-4 py-3 text-left text-gray-400 font-medium">Relevance</th>
                <th class="px-4 py-3 text-left text-gray-400 font-medium">Competition</th>
                <th class="px-4 py-3 text-left text-gray-400 font-medium">Timeliness</th>
                <th class="px-4 py-3 text-left text-gray-400 font-medium">Suggested Title</th>
            </tr>
        </thead>
        <tbody class="divide-y divide-gray-800">
            {''.join(rows)}
        </tbody>
    </table>
    """
    return HTMLResponse(html)
