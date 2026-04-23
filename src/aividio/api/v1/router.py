"""Main API v1 router — aggregates all sub-routers under /api/v1."""

from __future__ import annotations

from fastapi import APIRouter

from aividio.api.v1.agent import router as agent_router
from aividio.api.v1.assets import router as assets_router
from aividio.api.v1.billing import router as billing_router
from aividio.api.v1.channels import router as channels_router
from aividio.api.v1.generate import router as generate_router
from aividio.api.v1.jobs import router as jobs_router
from aividio.api.v1.publish import router as publish_router
from aividio.api.v1.videos import router as videos_router
from aividio.api.v1.webhooks_routes import router as webhooks_router

router = APIRouter()

# Each sub-router already carries its own prefix (/videos, /channels, etc.)
router.include_router(agent_router)
router.include_router(assets_router)
router.include_router(billing_router)
router.include_router(videos_router)
router.include_router(channels_router)
router.include_router(jobs_router)
router.include_router(generate_router)
router.include_router(publish_router)
router.include_router(webhooks_router)


@router.get("/health", tags=["meta"])
async def health_check():
    """Lightweight health-check endpoint — no auth required."""
    return {"status": "ok", "api_version": "v1"}
