"""Video API endpoints — multi-tenant CRUD, batch creation, export.

All endpoints are scoped to the authenticated user's videos only.
Supports both JWT auth (primary) and API key auth (legacy/programmatic).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from vidmation.api.v1.schemas import (
    BatchCreateRequest,
    BatchItemResponse,
    BatchResponse,
    ErrorResponse,
    PaginationParams,
    VideoCreateRequest,
    VideoExportRequest,
    VideoExportResponse,
    VideoListResponse,
    VideoResponse,
    VideoStatusResponse,
)
from vidmation.api.webhooks import WebhookManager
from vidmation.auth.dependencies import require_active_user
from vidmation.db.engine import get_session
from vidmation.db.repos import ChannelRepo, JobRepo, VideoRepo
from vidmation.models.channel import Channel
from vidmation.models.job import Job, JobStatus, JobType
from vidmation.models.user import User
from vidmation.models.video import Video, VideoFormat, VideoStatus

router = APIRouter(prefix="/videos", tags=["videos"])


# ---------------------------------------------------------------------------
# POST /videos — create a single video + start generation job
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=VideoResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def create_video(
    body: VideoCreateRequest,
    user: User = Depends(require_active_user),
):
    """Create a new video and enqueue a generation job."""
    session = get_session()
    try:
        # Validate channel exists and belongs to user
        stmt = select(Channel).where(
            Channel.id == body.channel_id,
            Channel.user_id == user.id,
        )
        channel = session.scalars(stmt).first()
        if channel is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Channel '{body.channel_id}' not found",
            )

        video_format = VideoFormat(body.format)

        video_repo = VideoRepo(session)
        video = video_repo.create(
            user_id=user.id,
            channel_id=body.channel_id,
            topic_prompt=body.topic,
            format=video_format,
            title=body.title,
            description=body.description,
            tags=body.tags,
            status=VideoStatus.DRAFT,
        )

        # Enqueue a full-pipeline job
        job_repo = JobRepo(session)
        job_repo.create(
            video_id=video.id,
            job_type=JobType.FULL_PIPELINE,
            status=JobStatus.QUEUED,
        )

        # Fire webhook
        try:
            wh = WebhookManager()
            wh.fire_sync("video.created", {"video_id": video.id, "topic": body.topic})
        except Exception:
            pass  # Webhook delivery is best-effort

        return VideoResponse.model_validate(video)

    finally:
        session.close()


# ---------------------------------------------------------------------------
# GET /videos — paginated list with optional filters (user-scoped)
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=VideoListResponse,
)
async def list_videos(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    channel_id: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    user: User = Depends(require_active_user),
):
    """List videos with pagination and optional filters (user-scoped)."""
    session = get_session()
    try:
        stmt = (
            select(Video)
            .where(Video.user_id == user.id)
            .order_by(Video.created_at.desc())
        )

        if channel_id:
            stmt = stmt.where(Video.channel_id == channel_id)
        if status_filter:
            stmt = stmt.where(Video.status == VideoStatus(status_filter))

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = session.execute(count_stmt).scalar() or 0

        # Paginate
        offset = (page - 1) * per_page
        stmt = stmt.offset(offset).limit(per_page)
        videos = list(session.scalars(stmt).all())

        total_pages = max(1, (total + per_page - 1) // per_page)

        return VideoListResponse(
            items=[VideoResponse.model_validate(v) for v in videos],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
        )
    finally:
        session.close()


# ---------------------------------------------------------------------------
# GET /videos/{id} — single video detail (user-scoped)
# ---------------------------------------------------------------------------


@router.get(
    "/{video_id}",
    response_model=VideoResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_video(
    video_id: str,
    user: User = Depends(require_active_user),
):
    """Get full details for a single video."""
    session = get_session()
    try:
        video = _get_user_video(session, video_id, user.id)
        return VideoResponse.model_validate(video)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# GET /videos/{id}/status — lightweight status check (user-scoped)
# ---------------------------------------------------------------------------


@router.get(
    "/{video_id}/status",
    response_model=VideoStatusResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_video_status(
    video_id: str,
    user: User = Depends(require_active_user),
):
    """Get the generation status for a video (lightweight)."""
    session = get_session()
    try:
        video = _get_user_video(session, video_id, user.id)

        # Find the most recent job for this video
        stmt = (
            select(Job)
            .where(Job.video_id == video_id)
            .order_by(Job.created_at.desc())
            .limit(1)
        )
        latest_job = session.scalars(stmt).first()

        return VideoStatusResponse(
            id=video.id,
            status=video.status.value,
            current_job_status=latest_job.status.value if latest_job else None,
            current_job_stage=latest_job.current_stage if latest_job else None,
            progress_pct=latest_job.progress_pct if latest_job else None,
        )
    finally:
        session.close()


# ---------------------------------------------------------------------------
# DELETE /videos/{id} (user-scoped)
# ---------------------------------------------------------------------------


@router.delete(
    "/{video_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}},
)
async def delete_video(
    video_id: str,
    user: User = Depends(require_active_user),
):
    """Delete a video and its associated jobs."""
    session = get_session()
    try:
        from sqlalchemy import delete as sql_delete

        video = _get_user_video(session, video_id, user.id)

        # Delete associated jobs first
        session.execute(sql_delete(Job).where(Job.video_id == video_id))
        session.delete(video)
        session.commit()

    finally:
        session.close()


# ---------------------------------------------------------------------------
# POST /videos/batch — bulk create from topic list (user-scoped)
# ---------------------------------------------------------------------------


@router.post(
    "/batch",
    response_model=BatchResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}},
)
async def batch_create_videos(
    body: BatchCreateRequest,
    user: User = Depends(require_active_user),
):
    """Create multiple videos from a list of topics."""
    session = get_session()
    try:
        # Validate channel belongs to user
        stmt = select(Channel).where(
            Channel.id == body.channel_id,
            Channel.user_id == user.id,
        )
        channel = session.scalars(stmt).first()
        if channel is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Channel '{body.channel_id}' not found",
            )

        video_format = VideoFormat(body.format)
        video_repo = VideoRepo(session)
        job_repo = JobRepo(session)
        batch_id = str(uuid.uuid4())
        items: list[BatchItemResponse] = []

        for topic in body.topics:
            video = video_repo.create(
                user_id=user.id,
                channel_id=body.channel_id,
                topic_prompt=topic,
                format=video_format,
                status=VideoStatus.DRAFT,
            )
            job = job_repo.create(
                video_id=video.id,
                job_type=JobType.FULL_PIPELINE,
                status=JobStatus.QUEUED,
            )
            items.append(
                BatchItemResponse(video_id=video.id, job_id=job.id, topic=topic)
            )

        # Fire batch webhook
        try:
            wh = WebhookManager()
            wh.fire_sync(
                "video.created",
                {"batch_id": batch_id, "count": len(items)},
            )
        except Exception:
            pass

        return BatchResponse(batch_id=batch_id, items=items, total=len(items))

    finally:
        session.close()


# ---------------------------------------------------------------------------
# POST /videos/{id}/export — export to platform (user-scoped)
# ---------------------------------------------------------------------------


@router.post(
    "/{video_id}/export",
    response_model=VideoExportResponse,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
async def export_video(
    video_id: str,
    body: VideoExportRequest,
    user: User = Depends(require_active_user),
):
    """Export a completed video to a platform (e.g. YouTube)."""
    session = get_session()
    try:
        video = _get_user_video(session, video_id, user.id)

        if video.status != VideoStatus.READY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Video is in '{video.status.value}' state. Must be 'ready' to export.",
            )

        # Create an upload job
        job_repo = JobRepo(session)
        job = job_repo.create(
            video_id=video.id,
            job_type=JobType.UPLOAD_ONLY,
            status=JobStatus.QUEUED,
        )

        return VideoExportResponse(
            video_id=video.id,
            platform=body.platform,
            status="queued",
            platform_url=None,
            job_id=job.id,
        )

    finally:
        session.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_user_video(session, video_id: str, user_id: str) -> Video:
    """Load a video and verify it belongs to the given user.

    Raises 404 if the video doesn't exist or doesn't belong to the user.
    """
    stmt = select(Video).where(
        Video.id == video_id,
        Video.user_id == user_id,
    )
    video = session.scalars(stmt).first()
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return video
