"""Pydantic v2 request/response schemas for the VIDMATION public API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

# ---------------------------------------------------------------------------
# Generic pagination
# ---------------------------------------------------------------------------

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Query parameters for paginated list endpoints."""

    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(20, ge=1, le=100, description="Items per page (max 100)")


class PaginatedResponse(BaseModel, Generic[T]):
    """Envelope for paginated list responses."""

    items: list[T]
    total: int = Field(description="Total number of items matching the query")
    page: int
    per_page: int
    total_pages: int


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    """Standard error envelope returned on 4xx/5xx."""

    detail: str
    code: str = "error"


# ---------------------------------------------------------------------------
# Channel schemas
# ---------------------------------------------------------------------------


class ChannelCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    youtube_channel_id: str | None = None
    profile_path: str = "channel_profiles/default.yml"
    is_active: bool = True


class ChannelUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    youtube_channel_id: str | None = None
    profile_path: str | None = None
    is_active: bool | None = None


class ChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    youtube_channel_id: str | None = None
    youtube_channel_title: str | None = None
    profile_path: str
    is_active: bool
    is_youtube_connected: bool = False
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Video schemas
# ---------------------------------------------------------------------------


class VideoCreateRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="Video topic / prompt")
    channel_id: str = Field(..., description="ID of the channel to create the video for")
    format: str = Field("landscape", pattern="^(landscape|portrait|short)$")
    title: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)


class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    channel_id: str
    title: str
    description: str
    tags: list[Any] | dict | None = None
    topic_prompt: str
    format: str
    status: str
    youtube_video_id: str | None = None
    youtube_url: str | None = None
    duration_seconds: float | None = None
    file_path: str | None = None
    thumbnail_path: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class VideoStatusResponse(BaseModel):
    """Lightweight status check for a video."""

    id: str
    status: str
    current_job_status: str | None = None
    current_job_stage: str | None = None
    progress_pct: int | None = None


class VideoListResponse(PaginatedResponse[VideoResponse]):
    """Paginated list of videos."""

    pass


class VideoExportRequest(BaseModel):
    platform: str = Field("youtube", description="Target platform for export")
    publish: bool = Field(False, description="Immediately publish after upload")


class VideoExportResponse(BaseModel):
    video_id: str
    platform: str
    status: str
    platform_url: str | None = None
    job_id: str | None = None


# ---------------------------------------------------------------------------
# Batch schemas
# ---------------------------------------------------------------------------


class BatchCreateRequest(BaseModel):
    topics: list[str] = Field(..., min_length=1, description="List of video topics")
    channel_id: str
    format: str = Field("landscape", pattern="^(landscape|portrait|short)$")


class BatchItemResponse(BaseModel):
    video_id: str
    job_id: str
    topic: str


class BatchResponse(BaseModel):
    batch_id: str
    items: list[BatchItemResponse]
    total: int


# ---------------------------------------------------------------------------
# Job schemas
# ---------------------------------------------------------------------------


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    video_id: str
    job_type: str
    status: str
    current_stage: str
    progress_pct: int
    resume_from_stage: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_detail: str | None = None
    created_at: datetime
    updated_at: datetime


class JobProgressResponse(BaseModel):
    id: str
    status: str
    current_stage: str
    progress_pct: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_detail: str | None = None


class JobLogEntry(BaseModel):
    timestamp: datetime
    level: str
    message: str


class JobLogsResponse(BaseModel):
    job_id: str
    logs: list[JobLogEntry]


class JobListResponse(PaginatedResponse[JobResponse]):
    """Paginated list of jobs."""

    pass


# ---------------------------------------------------------------------------
# Generate schemas
# ---------------------------------------------------------------------------


class GenerateScriptRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    channel_id: str | None = Field(None, description="Optional channel for style context")
    style: str = Field("educational", description="Script style / tone")
    duration_target_seconds: int = Field(
        300, ge=30, le=3600, description="Target video duration in seconds"
    )


class ScriptResponse(BaseModel):
    title: str
    description: str
    tags: list[str]
    sections: list[dict[str, Any]]
    estimated_duration_seconds: int
    word_count: int


class GenerateVoiceoverRequest(BaseModel):
    text: str = Field(..., min_length=1)
    voice_id: str = Field("default", description="TTS voice identifier")
    speed: float = Field(1.0, ge=0.5, le=2.0)


class VoiceoverResponse(BaseModel):
    file_path: str
    duration_seconds: float
    voice_id: str


class GenerateThumbnailRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    style: str = Field("youtube_thumbnail", description="Image generation style")
    width: int = Field(1280, ge=256, le=4096)
    height: int = Field(720, ge=256, le=4096)


class ThumbnailResponse(BaseModel):
    file_path: str
    width: int
    height: int


class GenerateVideoRequest(BaseModel):
    """Kick off the full video generation pipeline (async)."""

    topic: str = Field(..., min_length=1)
    channel_id: str
    format: str = Field("landscape", pattern="^(landscape|portrait|short)$")
    style: str = "educational"
    auto_upload: bool = False


class GenerateVideoResponse(BaseModel):
    video_id: str
    job_id: str
    status: str = "queued"


# ---------------------------------------------------------------------------
# Webhook schemas
# ---------------------------------------------------------------------------


class WebhookCreateRequest(BaseModel):
    url: str = Field(..., description="HTTPS endpoint to receive events")
    events: list[str] = Field(
        ...,
        min_length=1,
        description="List of event types to subscribe to",
    )
    secret: str | None = Field(None, description="Optional HMAC signing secret")
    description: str = ""


class WebhookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    url: str
    events: list[str]
    is_active: bool
    description: str
    failure_count: int
    last_triggered_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class WebhookTestResponse(BaseModel):
    webhook_id: str
    status: str
    response_code: int | None = None
    response_body: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# API Key schemas
# ---------------------------------------------------------------------------


class APIKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    rate_limit_per_minute: int = Field(60, ge=1, le=10000)


class APIKeyCreateResponse(BaseModel):
    """Returned only once at creation time — includes the raw key."""

    id: str
    name: str
    prefix: str
    key: str = Field(description="The full API key. Store it securely; it cannot be retrieved again.")
    rate_limit_per_minute: int
    created_at: datetime


class APIKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    prefix: str
    is_active: bool
    rate_limit_per_minute: int
    last_used_at: datetime | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Publish schemas
# ---------------------------------------------------------------------------


class PublishRequest(BaseModel):
    """Request body for publishing a video to one or more platforms."""

    video_id: str | None = Field(None, description="ID of an existing video to publish")
    video_path: str | None = Field(None, description="File path to a generated video")
    channel_id: str | None = Field(None, description="Channel ID to publish from")
    channel_name: str | None = Field(None, description="Channel name to publish from (alternative to channel_id)")
    title: str | None = Field(None, description="Video title (AI-generated if omitted)")
    description: str | None = Field(None, description="Video description (AI-generated if omitted)")
    tags: list[str] | None = Field(None, description="Video tags (AI-generated if omitted)")
    schedule: str | None = Field(
        None,
        description="ISO datetime or relative time (e.g. '+2h') to schedule publish",
    )
    platforms: list[str] = Field(
        default_factory=lambda: ["youtube"],
        description="Target platforms: youtube, tiktok, instagram",
    )


class PublishResponse(BaseModel):
    """Response from a successful publish request."""

    video_id: str
    channel_id: str
    youtube_video_id: str | None = None
    youtube_url: str | None = None
    platforms: list[str]
    status: str = Field(description="'published', 'scheduled', or 'queued'")
    scheduled_at: datetime | None = None
    job_id: str | None = None


class YouTubeConnectResponse(BaseModel):
    """Response containing the YouTube OAuth authorization URL."""

    auth_url: str
    channel_id: str
