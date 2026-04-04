"""Analytics routes - cost monitoring, performance tracking, and reports."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, timezone

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse

from vidmation.analytics.reports import ReportGenerator
from vidmation.analytics.tracker import get_tracker
from vidmation.web.app import get_templates

router = APIRouter()


@router.get("/analytics", response_class=HTMLResponse)
async def analytics_dashboard(request: Request):
    """Analytics overview dashboard with cost and performance summary."""
    templates = get_templates()
    tracker = get_tracker()
    reports = ReportGenerator()

    now = datetime.now(timezone.utc)

    # Get monthly cost data
    monthly = tracker.get_monthly_summary(now.year, now.month)

    # Get today's costs
    today = tracker.get_daily_summary(date.today())

    # Get cost report for charting
    cost_data = reports.cost_report(period="monthly")

    # Calculate cost per video average
    total_videos = len(cost_data.get("top_expensive_videos", []))
    cost_per_video_avg = (
        round(monthly["total_cost_usd"] / total_videos, 2)
        if total_videos > 0
        else 0.0
    )

    return templates.TemplateResponse(
        "analytics/dashboard.html",
        {
            "request": request,
            "monthly_cost": monthly["total_cost_usd"],
            "monthly_calls": monthly["total_calls"],
            "today_cost": today["total_cost_usd"],
            "today_calls": today["total_calls"],
            "cost_per_video_avg": cost_per_video_avg,
            "by_service": monthly.get("by_service", {}),
            "daily_trend": cost_data.get("daily_trend", []),
            "top_expensive_videos": cost_data.get("top_expensive_videos", []),
            "year": now.year,
            "month": now.month,
        },
    )


@router.get("/analytics/costs", response_class=HTMLResponse)
async def analytics_costs(
    request: Request,
    period: str = Query("monthly", regex="^(daily|weekly|monthly)$"),
    service: str | None = Query(None),
):
    """Detailed cost breakdown page with filtering."""
    templates = get_templates()
    tracker = get_tracker()
    reports = ReportGenerator()

    cost_data = reports.cost_report(period=period)

    # Get recent events, optionally filtered by service
    recent_events = tracker.get_recent_events(limit=200)
    if service:
        recent_events = [e for e in recent_events if e["service"] == service]

    # Compute running total
    running_total = 0.0
    for event in reversed(recent_events):
        running_total += event["cost_usd"]
        event["running_total"] = round(running_total, 4)

    # Get unique services for filter dropdown
    all_services = sorted(set(e["service"] for e in tracker.get_recent_events(limit=1000)))

    return templates.TemplateResponse(
        "analytics/costs.html",
        {
            "request": request,
            "period": period,
            "service_filter": service,
            "cost_data": cost_data,
            "events": recent_events,
            "all_services": all_services,
            "total_cost": cost_data["total_cost_usd"],
            "total_calls": cost_data["total_calls"],
        },
    )


@router.get("/analytics/performance", response_class=HTMLResponse)
async def analytics_performance(
    request: Request,
    channel_id: str | None = Query(None),
):
    """Video performance analytics page."""
    templates = get_templates()
    reports = ReportGenerator()

    perf = reports.performance_report(channel_id=channel_id)
    content = reports.content_report(channel_id=channel_id)
    efficiency = reports.efficiency_report()

    # Get channels for filter dropdown
    from vidmation.db.engine import get_session
    from vidmation.db.repos import ChannelRepo

    session = get_session()
    try:
        channel_repo = ChannelRepo(session)
        channels = channel_repo.list_all()
    finally:
        session.close()

    return templates.TemplateResponse(
        "analytics/performance.html",
        {
            "request": request,
            "channel_id": channel_id,
            "channels": channels,
            "performance": perf,
            "content": content,
            "efficiency": efficiency,
        },
    )


# ---------- JSON API Endpoints ----------


@router.get("/api/analytics/costs")
async def api_analytics_costs(
    period: str = Query("monthly", regex="^(daily|weekly|monthly)$"),
):
    """JSON cost data for charts and HTMX polling."""
    reports = ReportGenerator()
    return reports.cost_report(period=period)


@router.get("/api/analytics/video/{video_id}/cost")
async def api_video_cost(video_id: str):
    """Per-video cost breakdown as JSON."""
    tracker = get_tracker()
    return tracker.get_video_cost(video_id)


@router.get("/api/analytics/estimate")
async def api_estimate_cost(
    duration_minutes: float = Query(10.0, ge=1, le=120),
    llm_provider: str = Query("claude"),
    tts_provider: str = Query("elevenlabs"),
    image_provider: str = Query("dalle3"),
    num_images: int = Query(15, ge=1, le=100),
):
    """Pre-estimate the cost of generating a video."""
    tracker = get_tracker()
    return tracker.estimate_video_cost(
        duration_minutes=duration_minutes,
        llm_provider=llm_provider,
        tts_provider=tts_provider,
        image_provider=image_provider,
        num_images=num_images,
    )


@router.get("/api/analytics/costs/export")
async def api_export_costs_csv(
    period: str = Query("monthly", regex="^(daily|weekly|monthly)$"),
):
    """Export usage events as a CSV download."""
    tracker = get_tracker()
    events = tracker.get_recent_events(limit=10000)

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "timestamp", "service", "operation", "cost_usd",
            "tokens_used", "duration_seconds", "model_name",
            "video_id", "job_id",
        ],
    )
    writer.writeheader()
    for event in events:
        writer.writerow({
            "timestamp": event["timestamp"],
            "service": event["service"],
            "operation": event["operation"],
            "cost_usd": event["cost_usd"],
            "tokens_used": event.get("tokens_used", ""),
            "duration_seconds": event.get("duration_seconds", ""),
            "model_name": event.get("model_name", ""),
            "video_id": event.get("video_id", ""),
            "job_id": event.get("job_id", ""),
        })

    output.seek(0)
    today_str = date.today().isoformat()
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=vidmation_costs_{today_str}.csv"
        },
    )
