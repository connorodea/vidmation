"""Job monitoring routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from aividio.db.engine import get_session
from aividio.db.repos import JobRepo
from aividio.models.job import JobStatus
from aividio.web.templating import get_templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def job_list(request: Request, status: str | None = None):
    """List all jobs with optional status filter."""
    templates = get_templates()
    session = get_session()
    try:
        repo = JobRepo(session)
        filter_status = JobStatus(status) if status else None
        jobs = repo.list_all(status=filter_status, limit=50)
        return templates.TemplateResponse(
            "jobs/list.html",
            {
                "request": request,
                "jobs": jobs,
                "current_status": status,
                "statuses": [s.value for s in JobStatus],
            },
        )
    finally:
        session.close()


@router.get("/{job_id}", response_class=HTMLResponse)
async def job_detail(request: Request, job_id: str):
    """Job detail page with progress and logs."""
    templates = get_templates()
    session = get_session()
    try:
        repo = JobRepo(session)
        job = repo.get(job_id)
        if not job:
            return HTMLResponse("Job not found", status_code=404)
        return templates.TemplateResponse(
            "jobs/detail.html",
            {"request": request, "job": job},
        )
    finally:
        session.close()
