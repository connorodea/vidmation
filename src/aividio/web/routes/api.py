"""JSON API endpoints for HTMX and async operations."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from aividio.db.engine import get_session
from aividio.db.repos import JobRepo
from aividio.models.job import JobStatus

router = APIRouter()


@router.get("/jobs/{job_id}/progress")
async def job_progress(job_id: str):
    """Get job progress as JSON (polled by HTMX)."""
    session = get_session()
    try:
        repo = JobRepo(session)
        job = repo.get(job_id)
        if not job:
            return {"error": "Job not found"}
        return {
            "id": job.id,
            "status": job.status.value,
            "current_stage": job.current_stage,
            "progress_pct": job.progress_pct,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error_detail": job.error_detail,
        }
    finally:
        session.close()


@router.post("/jobs/{job_id}/cancel")
async def job_cancel(job_id: str):
    """Cancel a queued or running job."""
    session = get_session()
    try:
        repo = JobRepo(session)
        job = repo.get(job_id)
        if not job:
            return {"error": "Job not found"}
        if job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
            return {"status": "cancelled"}
        return {"error": f"Cannot cancel job with status {job.status.value}"}
    finally:
        session.close()


@router.post("/jobs/{job_id}/retry")
async def job_retry(job_id: str):
    """Retry a failed job from the failed stage."""
    session = get_session()
    try:
        repo = JobRepo(session)
        job = repo.get(job_id)
        if not job:
            return {"error": "Job not found"}
        if job.status != JobStatus.FAILED:
            return {"error": "Can only retry failed jobs"}

        # Create a new job that resumes from the failed stage
        new_job = repo.create(
            video_id=job.video_id,
            job_type=job.job_type,
            resume_from_stage=job.current_stage,
        )
        return {"status": "queued", "new_job_id": new_job.id}
    finally:
        session.close()
