"""Channel API endpoints — multi-tenant CRUD for YouTube channel configurations.

All endpoints are scoped to the authenticated user's channels only.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from vidmation.api.v1.schemas import (
    ChannelCreateRequest,
    ChannelResponse,
    ChannelUpdateRequest,
    ErrorResponse,
    PaginatedResponse,
    YouTubeConnectResponse,
)
from vidmation.auth.dependencies import require_active_user
from vidmation.db.engine import get_session
from vidmation.models.channel import Channel
from vidmation.models.user import User

logger = logging.getLogger(__name__)

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
    user: User = Depends(require_active_user),
):
    """Create a new channel configuration owned by the current user."""
    session = get_session()
    try:
        # Check for duplicate name within this user's channels
        stmt = select(Channel).where(
            Channel.user_id == user.id,
            Channel.name == body.name,
        )
        existing = session.scalars(stmt).first()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"You already have a channel named '{body.name}'",
            )

        channel = Channel(
            user_id=user.id,
            name=body.name,
            youtube_channel_id=body.youtube_channel_id,
            profile_path=body.profile_path,
            is_active=body.is_active,
        )
        session.add(channel)
        session.commit()
        session.refresh(channel)

        return ChannelResponse.model_validate(channel)

    finally:
        session.close()


# ---------------------------------------------------------------------------
# GET /channels — paginated list (user-scoped)
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=PaginatedResponse[ChannelResponse],
)
async def list_channels(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    active_only: bool = Query(True),
    user: User = Depends(require_active_user),
):
    """List all channels belonging to the current user."""
    session = get_session()
    try:
        stmt = (
            select(Channel)
            .where(Channel.user_id == user.id)
            .order_by(Channel.created_at.desc())
        )
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
# GET /channels/{id} — channel detail (user-scoped)
# ---------------------------------------------------------------------------


@router.get(
    "/{channel_id}",
    response_model=ChannelResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_channel(
    channel_id: str,
    user: User = Depends(require_active_user),
):
    """Get full details for a single channel, including YouTube connection status."""
    session = get_session()
    try:
        channel = _get_user_channel(session, channel_id, user.id)
        return ChannelResponse.model_validate(channel)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# PUT /channels/{id} — update channel (user-scoped)
# ---------------------------------------------------------------------------


@router.put(
    "/{channel_id}",
    response_model=ChannelResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def update_channel(
    channel_id: str,
    body: ChannelUpdateRequest,
    user: User = Depends(require_active_user),
):
    """Update an existing channel's configuration."""
    session = get_session()
    try:
        channel = _get_user_channel(session, channel_id, user.id)

        update_data = body.model_dump(exclude_unset=True)

        # Duplicate-name guard within user's channels
        if "name" in update_data and update_data["name"] != channel.name:
            stmt = select(Channel).where(
                Channel.user_id == user.id,
                Channel.name == update_data["name"],
            )
            if session.scalars(stmt).first() is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"You already have a channel named '{update_data['name']}'",
                )

        for key, value in update_data.items():
            setattr(channel, key, value)

        session.commit()
        session.refresh(channel)
        return ChannelResponse.model_validate(channel)

    finally:
        session.close()


# ---------------------------------------------------------------------------
# POST /channels/{id}/connect-youtube — initiate YouTube OAuth
# ---------------------------------------------------------------------------


@router.post(
    "/{channel_id}/connect-youtube",
    response_model=YouTubeConnectResponse,
    responses={404: {"model": ErrorResponse}},
)
async def connect_youtube(
    channel_id: str,
    user: User = Depends(require_active_user),
):
    """Initiate the YouTube OAuth flow for a channel.

    Returns an authorization URL that the user should open in their browser
    to grant YouTube access. After authorization, the OAuth callback will
    store the credentials on the channel.
    """
    session = get_session()
    try:
        channel = _get_user_channel(session, channel_id, user.id)

        try:
            from google_auth_oauthlib.flow import Flow

            from vidmation.config.settings import get_settings

            settings = get_settings()

            # Look for client_secret file in the data directory
            client_secret_path = settings.data_dir / "client_secret.json"
            if not client_secret_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail=(
                        "YouTube OAuth not configured. Place a client_secret.json "
                        "file in the data directory."
                    ),
                )

            scopes = [
                "https://www.googleapis.com/auth/youtube.upload",
                "https://www.googleapis.com/auth/youtube",
                "https://www.googleapis.com/auth/youtube.force-ssl",
            ]

            redirect_uri = (
                f"{settings.public_base_url}/api/v1/channels/{channel_id}/youtube-callback"
                if settings.public_base_url
                else f"http://localhost:{settings.web_port}/api/v1/channels/{channel_id}/youtube-callback"
            )

            flow = Flow.from_client_secrets_file(
                str(client_secret_path),
                scopes=scopes,
                redirect_uri=redirect_uri,
            )

            auth_url, _ = flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
                prompt="consent",
                state=channel.id,
            )

            return YouTubeConnectResponse(
                auth_url=auth_url,
                channel_id=channel.id,
            )

        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="YouTube OAuth libraries not installed (google-auth-oauthlib)",
            )

    finally:
        session.close()


# ---------------------------------------------------------------------------
# DELETE /channels/{id} — soft delete (user-scoped)
# ---------------------------------------------------------------------------


@router.delete(
    "/{channel_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}},
)
async def delete_channel(
    channel_id: str,
    user: User = Depends(require_active_user),
):
    """Soft-delete a channel by deactivating it."""
    session = get_session()
    try:
        channel = _get_user_channel(session, channel_id, user.id)
        channel.is_active = False
        session.commit()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_user_channel(session, channel_id: str, user_id: str) -> Channel:
    """Load a channel and verify it belongs to the given user.

    Raises 404 if the channel doesn't exist or doesn't belong to the user.
    """
    stmt = select(Channel).where(
        Channel.id == channel_id,
        Channel.user_id == user_id,
    )
    channel = session.scalars(stmt).first()
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel
