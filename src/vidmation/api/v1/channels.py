"""Channel API endpoints — CRUD for YouTube channel configurations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from vidmation.api.auth import require_api_key
from vidmation.api.v1.schemas import (
    ChannelCreateRequest,
    ChannelResponse,
    ChannelUpdateRequest,
    ErrorResponse,
    PaginatedResponse,
)
from vidmation.db.engine import get_session
from vidmation.db.repos import ChannelRepo
from vidmation.models.channel import Channel

router = APIRouter(prefix="/channels", tags=["channels"])


# ---------------------------------------------------------------------------
# POST /channels — create a new channel
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=ChannelResponse,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}},
)
async def create_channel(
    body: ChannelCreateRequest,
    api_key_id: str = Depends(require_api_key),
):
    """Create a new channel configuration."""
    session = get_session()
    try:
        channel_repo = ChannelRepo(session)

        # Check for duplicate name
        existing = channel_repo.get_by_name(body.name)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Channel with name '{body.name}' already exists",
            )

        channel = channel_repo.create(
            name=body.name,
            youtube_channel_id=body.youtube_channel_id,
            profile_path=body.profile_path,
            is_active=body.is_active,
        )
        return ChannelResponse.model_validate(channel)

    finally:
        session.close()


# ---------------------------------------------------------------------------
# GET /channels — paginated list
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=PaginatedResponse[ChannelResponse],
)
async def list_channels(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    active_only: bool = Query(True),
    api_key_id: str = Depends(require_api_key),
):
    """List all channels with pagination."""
    session = get_session()
    try:
        stmt = select(Channel).order_by(Channel.created_at.desc())
        if active_only:
            stmt = stmt.where(Channel.is_active.is_(True))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = session.execute(count_stmt).scalar() or 0

        offset = (page - 1) * per_page
        stmt = stmt.offset(offset).limit(per_page)
        channels = list(session.scalars(stmt).all())

        total_pages = max(1, (total + per_page - 1) // per_page)

        return PaginatedResponse[ChannelResponse](
            items=[ChannelResponse.model_validate(c) for c in channels],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
        )
    finally:
        session.close()


# ---------------------------------------------------------------------------
# GET /channels/{id} — channel detail
# ---------------------------------------------------------------------------


@router.get(
    "/{channel_id}",
    response_model=ChannelResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_channel(
    channel_id: str,
    api_key_id: str = Depends(require_api_key),
):
    """Get full details for a single channel."""
    session = get_session()
    try:
        channel_repo = ChannelRepo(session)
        channel = channel_repo.get(channel_id)
        if channel is None:
            raise HTTPException(status_code=404, detail="Channel not found")
        return ChannelResponse.model_validate(channel)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# PUT /channels/{id} — update channel
# ---------------------------------------------------------------------------


@router.put(
    "/{channel_id}",
    response_model=ChannelResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def update_channel(
    channel_id: str,
    body: ChannelUpdateRequest,
    api_key_id: str = Depends(require_api_key),
):
    """Update an existing channel's configuration."""
    session = get_session()
    try:
        channel = session.get(Channel, channel_id)
        if channel is None:
            raise HTTPException(status_code=404, detail="Channel not found")

        update_data = body.model_dump(exclude_unset=True)

        # Duplicate-name guard
        if "name" in update_data and update_data["name"] != channel.name:
            channel_repo = ChannelRepo(session)
            if channel_repo.get_by_name(update_data["name"]) is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Channel with name '{update_data['name']}' already exists",
                )

        for key, value in update_data.items():
            setattr(channel, key, value)

        session.commit()
        session.refresh(channel)
        return ChannelResponse.model_validate(channel)

    finally:
        session.close()


# ---------------------------------------------------------------------------
# DELETE /channels/{id}
# ---------------------------------------------------------------------------


@router.delete(
    "/{channel_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}},
)
async def delete_channel(
    channel_id: str,
    api_key_id: str = Depends(require_api_key),
):
    """Soft-delete a channel by deactivating it."""
    session = get_session()
    try:
        channel = session.get(Channel, channel_id)
        if channel is None:
            raise HTTPException(status_code=404, detail="Channel not found")

        channel.is_active = False
        session.commit()

    finally:
        session.close()
