"""Channel management routes."""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from vidmation.db.engine import get_session
from vidmation.db.repos import ChannelRepo
from vidmation.web.templating import get_templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def channel_list(request: Request):
    """List all channels."""
    templates = get_templates()
    session = get_session()
    try:
        repo = ChannelRepo(session)
        channels = repo.list_all(active_only=False)
        return templates.TemplateResponse(
            "channels/list.html",
            {"request": request, "channels": channels},
        )
    finally:
        session.close()


@router.get("/new", response_class=HTMLResponse)
async def channel_new(request: Request):
    """New channel form."""
    templates = get_templates()
    return templates.TemplateResponse(
        "channels/new.html",
        {"request": request},
    )


@router.post("/new")
async def channel_create(
    name: str = Form(...),
    niche: str = Form("general"),
    profile_path: str = Form("channel_profiles/default.yml"),
):
    """Create a new channel."""
    session = get_session()
    try:
        repo = ChannelRepo(session)
        channel = repo.create(name=name, profile_path=profile_path)
        return RedirectResponse(f"/channels/{channel.id}", status_code=303)
    finally:
        session.close()


@router.get("/{channel_id}", response_class=HTMLResponse)
async def channel_detail(request: Request, channel_id: str):
    """Channel detail page."""
    templates = get_templates()
    session = get_session()
    try:
        repo = ChannelRepo(session)
        channel = repo.get(channel_id)
        if not channel:
            return HTMLResponse("Channel not found", status_code=404)
        return templates.TemplateResponse(
            "channels/detail.html",
            {"request": request, "channel": channel},
        )
    finally:
        session.close()
