"""Job API endpoints — list, detail, cancel, retry, and logs."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from vidmation.api.auth import require_api_key
from vidmation.api.v1.schemas import (
    ErrorResponse,
    JobListResponse,
    JobLogEntry,
    JobLogsResponse,
    JobProgressResponse,
    JobResponse,
)
from vidmation.db.engine import get_session
from vidmation.db.repos import JobRepo, VideoRepo
from vidmation.models.job import Job, JobStatus, JobType
from vidmation.models.video import VideoStatus

router = APIRouter(prefix="/jobs", tags=["jobs"])


# ---------------------------------------------------------------------------
# GET /jobs — paginated list
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=JobListResponse,
)
async def list_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    video_id: str | None = Query(None),
    job_type: str | None = Query(None),
    api_key_id: str = Depends(require_api_key),
):
    """List jobs with pagination and optional filters."""
    session = get_session()
    try:
        stmt = select(Job).order_by(Job.created_at.desc())

        if status_filter:
            stmt = stmt.where(Job.status == JobStatus(status_filter))
        if video_id:
            stmt = stmt.where(Job.video_id == video_id)
        if job_type:
            stmt = stmt.where(Job.job_type == JobType(job_type))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = session.execute(count_stmt).scalar() or 0

        offset = (page - 1) * per_page
        stmt = stmt.offset(offset).limit(per_page)
        jobs = list(session.scalars(stmt).all())

        total_pages = max(1, (total + per_page - 1) // per_page)

        return JobListResponse(
            items=[JobResponse.model_validate(j) for j in jobs],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
        )
    finally:
        session.close()


# ---------------------------------------------------------------------------
# GET /jobs/{id} — job detail with progress
# ---------------------------------------------------------------------------


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_job(
    job_id: str,
    api_key_id: str = Depends(require_api_key),
):
    """Get full details and progress for a single job."""
    session = get_session()
    try:
        job_repo = JobRepo(session)
        job = job_repo.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return JobResponse.model_validate(job)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# POST /jobs/{id}/cancel
# ---------------------------------------------------------------------------


@router.post(
    "/{job_id}/cancel",
    response_model=JobProgressResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def cancel_job(
    job_id: str,
    api_key_id: str = Depends(require_api_key),
):
    """Cancel a queued or running job."""
    session = get_session()
    try:
        job_repo = JobRepo(session)
        job = job_repo.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status not in (JobStatus.QUEUED, JobStatus.RUNNING):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot cancel job with status '{job.status.value}'",
            )

        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(job)

        return JobProgressResponse(
            id=job.id,
            status=job.status.value,
            current_stage=job.current_stage,
            progress_pct=job.progress_pct,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_detail=job.error_detail,
        )
    finally:
        session.close()


# ---------------------------------------------------------------------------
# POST /jobs/{id}/retry
# ---------------------------------------------------------------------------


@router.post(
    "/{job_id}/retry",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def retry_job(
    job_id: str,
    api_key_id: str = Depends(require_api_key),
):
    """Retry a failed or cancelled job, creating a new job record."""
    session = get_session()
    try:
        job_repo = JobRepo(session)
        original = job_repo.get(job_id)
        if original is None:
            raise HTTPException(status_code=404, detail="Job not found")

        if original.status not in (JobStatus.FAILED, JobStatus.CANCELLED):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Only FAILED or CANCELLED jobs can be retried (current: {original.status.value})",
            )

        new_job = job_repo.create(
            video_id=original.video_id,
            job_type=original.job_type,
            status=JobStatus.QUEUED,
            resume_from_stage=original.current_stage or None,
        )

        # Reset the associated video to draft so the pipeline can proceed
        video_repo = VideoRepo(session)
        video_repo.update_status(original.video_id, VideoStatus.DRAFT)

        return JobResponse.model_validate(new_job)

    finally:
        session.close()


# ---------------------------------------------------------------------------
# GET /jobs/{id}/logs — job execution logs
# ---------------------------------------------------------------------------


@router.get(
    "/{job_id}/logs",
    response_model=JobLogsResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_job_logs(
    job_id: str,
    api_key_id: str = Depends(require_api_key),
):
    """Get execution logs for a job.

    Note: In the current implementation logs are synthesized from job metadata.
    A future release will store granular log entries in a dedicated table.
    """
    session = get_session()
    try:
        job_repo = JobRepo(session)
        job = job_repo.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")

        # Build a synthetic log from available metadata
        logs: list[JobLogEntry] = []

        logs.append(
            JobLogEntry(
                timestamp=job.created_at,
                level="INFO",
                message=f"Job created: type={job.job_type.value}",
            )
        )

        if job.started_at:
            logs.append(
                JobLogEntry(
                    timestamp=job.started_at,
                    level="INFO",
                    message="Job started",
                )
            )

        if job.current_stage:
            ts = job.started_at or job.created_at
            logs.append(
                JobLogEntry(
                    timestamp=ts,
                    level="INFO",
                    message=f"Stage: {job.current_stage} (progress: {job.progress_pct}%)",
                )
            )

        if job.status == JobStatus.COMPLETED and job.completed_at:
            logs.append(
                JobLogEntry(
                    timestamp=job.completed_at,
                    level="INFO",
                    message="Job completed successfully",
                )
            )

        if job.status == JobStatus.FAILED:
            ts = job.completed_at or job.created_at
            logs.append(
                JobLogEntry(
                    timestamp=ts,
                    level="ERROR",
                    message=f"Job failed: {job.error_detail or 'unknown error'}",
                )
            )

        if job.status == JobStatus.CANCELLED and job.completed_at:
            logs.append(
                JobLogEntry(
                    timestamp=job.completed_at,
                    level="WARNING",
                    message="Job cancelled",
                )
            )

        return JobLogsResponse(job_id=job.id, logs=logs)

    finally:
        session.close()
