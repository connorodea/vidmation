"""Video management routes."""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from vidmation.db.engine import get_session
from vidmation.db.repos import ChannelRepo, VideoRepo
from vidmation.models.video import VideoFormat, VideoStatus
from vidmation.queue.tasks import enqueue_video
from vidmation.web.templating import get_templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def video_list(request: Request, status: str | None = None):
    """List all videos with optional status filter."""
    templates = get_templates()
    session = get_session()
    try:
        repo = VideoRepo(session)
        filter_status = VideoStatus(status) if status else None
        videos = repo.list_all(status=filter_status, limit=50)
        return templates.TemplateResponse(
            "videos/list.html",
            {
                "request": request,
                "videos": videos,
                "current_status": status,
                "statuses": [s.value for s in VideoStatus],
            },
        )
    finally:
        session.close()


@router.get("/new", response_class=HTMLResponse)
async def video_new(request: Request):
    """New video creation form."""
    templates = get_templates()
    session = get_session()
    try:
        channel_repo = ChannelRepo(session)
        channels = channel_repo.list_all()
        return templates.TemplateResponse(
            "videos/new.html",
            {
                "request": request,
                "channels": channels,
                "formats": [f.value for f in VideoFormat],
            },
        )
    finally:
        session.close()


@router.post("/new")
async def video_create(
    topic: str = Form(...),
    channel_id: str = Form(...),
    format: str = Form("landscape"),
):
    """Create a new video and queue generation job."""
    session = get_session()
    try:
        channel_repo = ChannelRepo(session)
        channel = channel_repo.get(channel_id)
        if not channel:
            return RedirectResponse("/videos/new?error=channel_not_found", status_code=303)

        video, job = enqueue_video(
            topic=topic,
            channel_name=channel.name,
            format=VideoFormat(format),
        )
        return RedirectResponse(f"/videos/{video.id}", status_code=303)
    finally:
        session.close()


@router.get("/{video_id}", response_class=HTMLResponse)
async def video_detail(request: Request, video_id: str):
    """Video detail page with metadata, stages, and preview."""
    templates = get_templates()
    session = get_session()
    try:
        repo = VideoRepo(session)
        video = repo.get(video_id)
        if not video:
            return HTMLResponse("Video not found", status_code=404)
        return templates.TemplateResponse(
            "videos/detail.html",
            {
                "request": request,
                "video": video,
            },
        )
    finally:
        session.close()
