"""FastAPI application factory for the VIDMATION web dashboard."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from vidmation.api.v1.router import router as api_v1_router
from vidmation.db.engine import init_db
from vidmation.web.routes import analytics, api, channels, content, dashboard, jobs, notifications, schedule, videos, voices

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="VIDMATION",
        description="AI-powered faceless YouTube video automation",
        version="0.1.0",
    )

    # Initialize database tables
    init_db()

    # Mount static files
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

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


def get_templates() -> Jinja2Templates:
    """Get Jinja2 templates instance."""
    return Jinja2Templates(directory=str(TEMPLATES_DIR))
