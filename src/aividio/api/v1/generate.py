"""Direct generation endpoints — script, voiceover, thumbnail, full video.

All endpoints require JWT authentication and scope data to the authenticated user.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from aividio.api.v1.schemas import (
    ErrorResponse,
    GenerateScriptRequest,
    GenerateThumbnailRequest,
    GenerateVideoRequest,
    GenerateVideoResponse,
    GenerateVoiceoverRequest,
    ScriptResponse,
    ThumbnailResponse,
    VoiceoverResponse,
)
from aividio.api.webhooks import WebhookManager
from aividio.auth.dependencies import require_active_user
from aividio.db.engine import get_session
from aividio.db.repos import JobRepo, VideoRepo
from aividio.models.channel import Channel
from aividio.models.job import JobStatus, JobType
from aividio.models.user import User
from aividio.models.video import VideoFormat, VideoStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate", tags=["generate"])


# ---------------------------------------------------------------------------
# POST /generate/script — generate a script and return JSON
# ---------------------------------------------------------------------------


@router.post(
    "/script",
    response_model=ScriptResponse,
    responses={500: {"model": ErrorResponse}},
)
async def generate_script(
    body: GenerateScriptRequest,
    user: User = Depends(require_active_user),
):
    """Generate a video script from a topic. Returns structured script JSON.

    This endpoint runs the script generation step synchronously and returns the
    result.  For large-scale production use, prefer creating a video with
    ``POST /api/v1/videos`` which runs the full pipeline asynchronously.
    """
    try:
        from aividio.services.script import ScriptGenerator
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Script generation service is not available in this deployment",
        )

    try:
        session = get_session()
        try:
            # Resolve channel profile for style context (optional, user-scoped)
            profile = None
            if body.channel_id:
                stmt = select(Channel).where(
                    Channel.id == body.channel_id,
                    Channel.user_id == user.id,
                )
                channel = session.scalars(stmt).first()
                if channel:
                    try:
                        from aividio.config.profiles import load_profile

                        profile = load_profile(channel.profile_path)
                    except Exception:
                        pass  # Use defaults if profile loading fails
        finally:
            session.close()

        generator = ScriptGenerator()
        result = generator.generate(
            topic=body.topic,
            style=body.style,
            duration_target=body.duration_target_seconds,
            profile=profile,
        )

        return ScriptResponse(
            title=result.get("title", body.topic),
            description=result.get("description", ""),
            tags=result.get("tags", []),
            sections=result.get("sections", []),
            estimated_duration_seconds=result.get(
                "estimated_duration_seconds", body.duration_target_seconds
            ),
            word_count=result.get("word_count", 0),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Script generation failed for topic=%r", body.topic)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Script generation failed: {exc}",
        )


# ---------------------------------------------------------------------------
# POST /generate/voiceover — generate TTS from text
# ---------------------------------------------------------------------------


@router.post(
    "/voiceover",
    response_model=VoiceoverResponse,
    responses={500: {"model": ErrorResponse}},
)
async def generate_voiceover(
    body: GenerateVoiceoverRequest,
    user: User = Depends(require_active_user),
):
    """Generate a voiceover audio file from text using TTS."""
    try:
        from aividio.services.tts import TTSService
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="TTS service is not available in this deployment",
        )

    try:
        tts = TTSService()
        result = tts.synthesize(
            text=body.text,
            voice_id=body.voice_id,
            speed=body.speed,
        )

        return VoiceoverResponse(
            file_path=result.get("file_path", ""),
            duration_seconds=result.get("duration_seconds", 0.0),
            voice_id=body.voice_id,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Voiceover generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voiceover generation failed: {exc}",
        )


# ---------------------------------------------------------------------------
# POST /generate/thumbnail — generate a thumbnail image from a prompt
# ---------------------------------------------------------------------------


@router.post(
    "/thumbnail",
    response_model=ThumbnailResponse,
    responses={500: {"model": ErrorResponse}},
)
async def generate_thumbnail(
    body: GenerateThumbnailRequest,
    user: User = Depends(require_active_user),
):
    """Generate a thumbnail image from a text prompt."""
    try:
        from aividio.services.image import ImageGenerator
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Image generation service is not available in this deployment",
        )

    try:
        generator = ImageGenerator()
        result = generator.generate(
            prompt=body.prompt,
            style=body.style,
            width=body.width,
            height=body.height,
        )

        return ThumbnailResponse(
            file_path=result.get("file_path", ""),
            width=body.width,
            height=body.height,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Thumbnail generation failed for prompt=%r", body.prompt)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Thumbnail generation failed: {exc}",
        )


# ---------------------------------------------------------------------------
# POST /generate/video — full async pipeline (returns job_id, user-scoped)
# ---------------------------------------------------------------------------


@router.post(
    "/video",
    response_model=GenerateVideoResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={404: {"model": ErrorResponse}},
)
async def generate_video(
    body: GenerateVideoRequest,
    user: User = Depends(require_active_user),
):
    """Kick off the full video generation pipeline asynchronously.

    Returns immediately with a ``video_id`` and ``job_id``.  Poll
    ``GET /api/v1/jobs/{job_id}`` or register a webhook for progress updates.
    """
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
        video = video_repo.create(
            user_id=user.id,
            channel_id=body.channel_id,
            topic_prompt=body.topic,
            format=video_format,
            status=VideoStatus.DRAFT,
        )

        job_repo = JobRepo(session)
        job = job_repo.create(
            video_id=video.id,
            job_type=JobType.FULL_PIPELINE,
            status=JobStatus.QUEUED,
        )

        # Fire webhook
        try:
            wh = WebhookManager()
            wh.fire_sync("video.created", {"video_id": video.id, "topic": body.topic})
        except Exception:
            pass

        return GenerateVideoResponse(
            video_id=video.id,
            job_id=job.id,
            status="queued",
        )

    finally:
        session.close()
