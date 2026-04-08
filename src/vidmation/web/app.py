"""FastAPI application factory for the VIDMATION web dashboard."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from vidmation.api.v1.router import router as api_v1_router
from vidmation.auth.routes import router as auth_router
from vidmation.db.engine import init_db
from vidmation.web.templating import get_templates  # noqa: F401 — re-exported for back-compat

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Import route modules here (after templating is available) to avoid
    # the circular-import caused by routes importing get_templates from this
    # module before it is fully initialised.
    from vidmation.web.routes import (  # noqa: PLC0415
        analytics,
        api,
        channels,
        content,
        dashboard,
        jobs,
        notifications,
        schedule,
        videos,
        voices,
    )

    app = FastAPI(
        title="AIVIDIO",
        description="AI-powered faceless YouTube video automation — aividio.com",
        version="0.1.0",
    )

    # Initialize database tables
    init_db()

    # Mount static files
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # --- Authentication (JWT) ---
    app.include_router(auth_router, tags=["auth"])

    # Include routers
    app.include_router(dashboard.router)
    app.include_router(videos.router, prefix="/videos", tags=["videos"])
    app.include_router(channels.router, prefix="/channels", tags=["channels"])
    app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
    app.include_router(api.router, prefix="/api", tags=["api"])
    app.include_router(voices.router, prefix="/voices", tags=["voices"])
    app.include_router(analytics.router, tags=["analytics"])
    app.include_router(content.router, prefix="/content", tags=["content"])
    app.include_router(schedule.router, tags=["schedule"])
    app.include_router(notifications.router, tags=["notifications"])

    # --- Public REST API v1 (JSON, API-key auth) ---
    app.include_router(api_v1_router, prefix="/api/v1")

    return app
