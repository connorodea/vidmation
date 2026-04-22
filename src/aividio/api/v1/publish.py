"""Publish API endpoint — upload and schedule videos to platforms.

Supports YouTube (primary), with stubs for TikTok and Instagram.
All endpoints are scoped to the authenticated user via JWT.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from aividio.api.v1.schemas import (
    ErrorResponse,
    PublishRequest,
    PublishResponse,
)
from aividio.auth.dependencies import require_active_user
from aividio.db.engine import get_session
from aividio.db.repos import JobRepo, VideoRepo
from aividio.models.channel import Channel
from aividio.models.job import JobStatus, JobType
from aividio.models.user import User
from aividio.models.video import Video, VideoStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/publish", tags=["publish"])

# Supported platforms
SUPPORTED_PLATFORMS = {"youtube", "tiktok", "instagram"}


# ---------------------------------------------------------------------------
# POST /publish — publish or schedule a video
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=PublishResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def publish_video(
    body: PublishRequest,
    user: User = Depends(require_active_user),
):
    """Publish a video to one or more platforms.

    Accepts either a ``video_id`` (reference to a generated video in the system)
    or a ``video_path`` (file system path to a video file). Exactly one of
    ``channel_id`` or ``channel_name`` must be provided.

    If ``title``, ``description``, or ``tags`` are omitted, they will be
    populated from the video record (which may have been AI-generated during
    the pipeline).

    Optionally schedule the publish with ``schedule`` (ISO 8601 datetime or
    relative offset like ``+2h``, ``+30m``, ``+1d``).

    Returns the YouTube video ID and URL on immediate success, or job details
    if the publish is queued/scheduled.
    """
    # --- Validate platforms ---
    invalid_platforms = set(body.platforms) - SUPPORTED_PLATFORMS
    if invalid_platforms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported platform(s): {', '.join(sorted(invalid_platforms))}. "
            f"Supported: {', '.join(sorted(SUPPORTED_PLATFORMS))}",
        )

    if not body.platforms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one platform must be specified",
        )

    # --- Must provide video_id or video_path ---
    if not body.video_id and not body.video_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'video_id' or 'video_path' must be provided",
        )

    # --- Must provide channel_id or channel_name ---
    if not body.channel_id and not body.channel_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'channel_id' or 'channel_name' must be provided",
        )

    session = get_session()
    try:
        # --- Resolve channel (user-scoped) ---
        channel = _resolve_channel(session, user.id, body.channel_id, body.channel_name)

        # --- Verify YouTube connection for YouTube publishes ---
        if "youtube" in body.platforms and not channel.is_youtube_connected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Channel '{channel.name}' is not connected to YouTube. "
                    f"Use POST /api/v1/channels/{channel.id}/connect-youtube first."
                ),
            )

        # --- Resolve or create video record ---
        video = _resolve_video(session, user.id, channel.id, body)

        # --- Parse schedule ---
        scheduled_at = _parse_schedule(body.schedule) if body.schedule else None

        # --- Override metadata if provided ---
        if body.title is not None:
            video.title = body.title
        if body.description is not None:
            video.description = body.description
        if body.tags is not None:
            video.tags = body.tags

        session.commit()
        session.refresh(video)

        # --- Create an upload/publish job ---
        job_repo = JobRepo(session)
        job = job_repo.create(
            video_id=video.id,
            job_type=JobType.UPLOAD_ONLY,
            status=JobStatus.QUEUED,
        )

        # --- If scheduling, create a schedule record ---
        publish_status = "queued"
        if scheduled_at:
            try:
                from aividio.models.schedule import Schedule, ScheduleStatus, ScheduleType

                schedule_record = Schedule(
                    channel_id=channel.id,
                    video_id=video.id,
                    schedule_type=ScheduleType.ONE_TIME,
                    publish_at=scheduled_at,
                    platforms=body.platforms,
                    status=ScheduleStatus.ACTIVE,
                    next_run_at=scheduled_at,
                )
                session.add(schedule_record)
                session.commit()
                publish_status = "scheduled"
                logger.info(
                    "Video %s scheduled for publish at %s on %s",
                    video.id[:8],
                    scheduled_at.isoformat(),
                    body.platforms,
                )
            except Exception:
                logger.warning("Failed to create schedule record; publishing immediately")
                scheduled_at = None

        # --- Fire webhook ---
        try:
            from aividio.api.webhooks import WebhookManager

            wh = WebhookManager()
            wh.fire_sync(
                "video.publish_requested",
                {
                    "video_id": video.id,
                    "channel_id": channel.id,
                    "platforms": body.platforms,
                    "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
                },
            )
        except Exception:
            pass  # Webhook delivery is best-effort

        return PublishResponse(
            video_id=video.id,
            channel_id=channel.id,
            youtube_video_id=video.youtube_video_id,
            youtube_url=video.youtube_url,
            platforms=body.platforms,
            status=publish_status,
            scheduled_at=scheduled_at,
            job_id=job.id,
        )

    finally:
        session.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_channel(
    session, user_id: str, channel_id: str | None, channel_name: str | None
) -> Channel:
    """Look up a channel by ID or name, ensuring it belongs to the user."""
    if channel_id:
        stmt = select(Channel).where(
            Channel.id == channel_id,
            Channel.user_id == user_id,
            Channel.is_active.is_(True),
        )
    else:
        stmt = select(Channel).where(
            Channel.name == channel_name,
            Channel.user_id == user_id,
            Channel.is_active.is_(True),
        )

    channel = session.scalars(stmt).first()
    if channel is None:
        identifier = channel_id or channel_name
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Channel '{identifier}' not found or not owned by you",
        )
    return channel


def _resolve_video(
    session, user_id: str, channel_id: str, body: PublishRequest
) -> Video:
    """Resolve an existing video or create a placeholder for a file-path publish."""
    if body.video_id:
        # Load existing video, ensure it belongs to the user
        stmt = select(Video).where(
            Video.id == body.video_id,
            Video.user_id == user_id,
        )
        video = session.scalars(stmt).first()
        if video is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video '{body.video_id}' not found or not owned by you",
            )

        if video.status not in (VideoStatus.READY, VideoStatus.UPLOADED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Video is in '{video.status.value}' state. "
                    "Must be 'ready' or 'uploaded' to publish."
                ),
            )

        return video

    # Create a new video record from the file path
    video_repo = VideoRepo(session)
    video = video_repo.create(
        user_id=user_id,
        channel_id=channel_id,
        topic_prompt=body.title or "Manual upload",
        title=body.title or "",
        description=body.description or "",
        tags=body.tags or [],
        file_path=body.video_path,
        status=VideoStatus.READY,
    )
    return video


def _parse_schedule(schedule_str: str) -> datetime:
    """Parse a schedule string into a UTC datetime.

    Accepts:
    - ISO 8601 datetime strings (e.g. "2025-06-15T14:00:00Z")
    - Relative offsets: "+2h", "+30m", "+1d", "+2h30m"
    """
    # Try relative offset first
    relative_pattern = r"^\+(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?$"
    match = re.match(relative_pattern, schedule_str.strip())
    if match:
        days = int(match.group(1) or 0)
        hours = int(match.group(2) or 0)
        minutes = int(match.group(3) or 0)

        if days == 0 and hours == 0 and minutes == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid schedule offset: '{schedule_str}'. Use e.g. '+2h', '+30m', '+1d'.",
            )

        return datetime.now(timezone.utc) + timedelta(days=days, hours=hours, minutes=minutes)

    # Try ISO 8601 parsing
    try:
        dt = datetime.fromisoformat(schedule_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Scheduled time must be in the future",
            )
        return dt
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid schedule format: '{schedule_str}'. "
                "Use ISO 8601 (e.g. '2025-06-15T14:00:00Z') or "
                "relative offset (e.g. '+2h', '+30m', '+1d')."
            ),
        )
