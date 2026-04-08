"""API endpoints for AI agent video creation."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from vidmation.auth.dependencies import require_active_user
from vidmation.config.profiles import ChannelProfile, get_default_profile, load_profile
from vidmation.config.settings import get_settings
from vidmation.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])

# ── In-memory job tracking (upgrade to Redis/DB for production) ──────────────

_agent_jobs: dict[str, dict[str, Any]] = {}


# ── Request / Response schemas ───────────────────────────────────────────────


class AgentCreateRequest(BaseModel):
    """Request body for starting AI-guided video creation."""

    topic: str = Field(..., description="Video topic or prompt.")
    channel: str = Field("default", description="Channel profile name.")
    target_duration: str = Field("10-12 minutes", description="Target video duration.")
    format: str = Field("landscape", description="Video format: landscape, portrait, short.")
    upload: bool = Field(False, description="Upload to YouTube when done.")
    budget_limit: float | None = Field(None, description="Maximum budget in USD.")


class AgentPlanRequest(BaseModel):
    """Request body for generating a production plan."""

    topic: str = Field(..., description="Video topic to plan for.")
    channel: str = Field("default", description="Channel profile name.")


class AgentJobResponse(BaseModel):
    """Response for async agent job creation."""

    job_id: str
    status: str
    message: str


class AgentPlanResponse(BaseModel):
    """Response for production plan."""

    topic: str
    plan: str


class AgentReviewResponse(BaseModel):
    """Response for video review."""

    video_id: str
    review: str


class AgentJobStatusResponse(BaseModel):
    """Response for job status polling."""

    job_id: str
    status: str
    video_id: str | None = None
    error: str | None = None
    result: dict[str, Any] | None = None


# ── Helper ───────────────────────────────────────────────────────────────────


def _resolve_profile(channel: str) -> ChannelProfile:
    """Load a channel profile by name."""
    if channel == "default":
        return get_default_profile()

    settings = get_settings()
    for ext in (".yaml", ".yml"):
        path = settings.profiles_dir / f"{channel}{ext}"
        if path.exists():
            return load_profile(path)

    return get_default_profile()


# ── Background task runner ───────────────────────────────────────────────────


def _run_agent_create(
    job_id: str,
    topic: str,
    channel: str,
    target_duration: str,
    format: str,
    upload: bool,
    budget_limit: float | None,
) -> None:
    """Background task that runs the agent orchestrator."""
    from vidmation.agent.orchestrator import AgentOrchestrator

    _agent_jobs[job_id]["status"] = "running"

    try:
        settings = get_settings()
        profile = _resolve_profile(channel)
        agent = AgentOrchestrator(settings=settings)

        ctx = agent.create_video(
            topic=topic,
            channel_profile=profile,
            target_duration=target_duration,
            format=format,
            upload=upload,
            budget_limit=budget_limit,
        )

        toolkit = getattr(agent, "_toolkit", None)
        total_cost = toolkit.total_cost if toolkit else 0.0

        _agent_jobs[job_id].update({
            "status": "completed",
            "video_id": ctx.video_id,
            "result": {
                "video_id": ctx.video_id,
                "title": ctx.script.get("title", "") if ctx.script else "",
                "final_video_path": str(ctx.final_video_path) if ctx.final_video_path else None,
                "thumbnail_path": str(ctx.thumbnail_path) if ctx.thumbnail_path else None,
                "voiceover_duration": ctx.voiceover_duration,
                "total_cost": total_cost,
                "stages_completed": ctx.completed_stages,
                "work_dir": str(ctx.work_dir),
            },
        })

    except Exception as exc:
        logger.error("Agent job %s failed: %s", job_id, exc, exc_info=True)
        _agent_jobs[job_id].update({
            "status": "failed",
            "error": str(exc),
        })


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/create", response_model=AgentJobResponse)
async def create_video(
    request: AgentCreateRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_active_user),
) -> AgentJobResponse:
    """Start AI-guided video creation (async).

    Returns a ``job_id`` immediately.  Poll ``GET /api/v1/agent/status/{job_id}``
    to check progress and get the result when complete.
    """
    job_id = str(uuid.uuid4())

    _agent_jobs[job_id] = {
        "status": "queued",
        "topic": request.topic,
        "video_id": None,
        "error": None,
        "result": None,
    }

    background_tasks.add_task(
        _run_agent_create,
        job_id=job_id,
        topic=request.topic,
        channel=request.channel,
        target_duration=request.target_duration,
        format=request.format,
        upload=request.upload,
        budget_limit=request.budget_limit,
    )

    return AgentJobResponse(
        job_id=job_id,
        status="queued",
        message=f"Agent job started for topic: {request.topic}",
    )


@router.get("/status/{job_id}", response_model=AgentJobStatusResponse)
async def get_job_status(
    job_id: str,
    user: User = Depends(require_active_user),
) -> AgentJobStatusResponse:
    """Check the status of an agent creation job."""
    job = _agent_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    return AgentJobStatusResponse(
        job_id=job_id,
        status=job["status"],
        video_id=job.get("video_id"),
        error=job.get("error"),
        result=job.get("result"),
    )


@router.post("/plan", response_model=AgentPlanResponse)
async def plan_video(
    request: AgentPlanRequest,
    user: User = Depends(require_active_user),
) -> AgentPlanResponse:
    """Generate a production plan without executing it.

    Synchronous -- returns the plan text directly.
    """
    from vidmation.agent.orchestrator import AgentOrchestrator

    settings = get_settings()
    profile = _resolve_profile(request.channel)

    try:
        agent = AgentOrchestrator(settings=settings)
        plan = agent.plan_video(topic=request.topic, channel_profile=profile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Plan generation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Plan generation failed: {exc}")

    return AgentPlanResponse(topic=request.topic, plan=plan)


@router.post("/review/{video_id}", response_model=AgentReviewResponse)
async def review_video(
    video_id: str,
    user: User = Depends(require_active_user),
) -> AgentReviewResponse:
    """AI reviews an existing video and suggests improvements."""
    import json
    from pathlib import Path

    from vidmation.agent.orchestrator import AgentOrchestrator
    from vidmation.pipeline.context import PipelineContext

    settings = get_settings()
    context_path = settings.output_dir / video_id / "pipeline_context.json"

    if not context_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Pipeline context not found for video {video_id}.",
        )

    try:
        context_data = json.loads(context_path.read_text(encoding="utf-8"))
        profile = get_default_profile()

        ctx = PipelineContext(
            video_id=video_id,
            channel_profile=profile,
            topic=context_data.get("topic", "Unknown"),
            format=context_data.get("format", "landscape"),
            work_dir=Path(context_data.get("work_dir", str(settings.output_dir / video_id))),
        )
        ctx.script = context_data.get("script")
        ctx.voiceover_duration = context_data.get("voiceover_duration")
        ctx.completed_stages = context_data.get("completed_stages", [])

        agent = AgentOrchestrator(settings=settings)
        review = agent.review_video(ctx)

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Review failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Review failed: {exc}")

    return AgentReviewResponse(video_id=video_id, review=review)
