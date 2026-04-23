"""Dashboard route - main landing page."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from aividio.db.engine import get_session
from aividio.db.repos import ChannelRepo, JobRepo, VideoRepo
from aividio.models.job import JobStatus
from aividio.models.video import VideoStatus
from aividio.web.templating import get_templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard with overview stats and recent activity."""
    templates = get_templates()
    session = get_session()
    try:
        video_repo = VideoRepo(session)
        job_repo = JobRepo(session)
        channel_repo = ChannelRepo(session)

        recent_videos = video_repo.list_all(limit=10)
        active_jobs = job_repo.list_all(status=JobStatus.RUNNING, limit=5)
        queued_jobs = job_repo.list_all(status=JobStatus.QUEUED, limit=5)
        channels = channel_repo.list_all()

        stats = {
            "total_videos": len(video_repo.list_all(limit=1000)),
            "uploaded_videos": len(video_repo.list_all(status=VideoStatus.UPLOADED, limit=1000)),
            "active_jobs": len(active_jobs),
            "queued_jobs": len(queued_jobs),
            "channels": len(channels),
        }

        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "stats": stats,
                "recent_videos": recent_videos,
                "active_jobs": active_jobs,
                "queued_jobs": queued_jobs,
                "channels": channels,
            },
        )
    finally:
        session.close()
