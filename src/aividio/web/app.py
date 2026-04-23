"""FastAPI application factory for the AIVIDIO web dashboard."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from aividio.api.v1.router import router as api_v1_router
from aividio.auth.routes import router as auth_router
from aividio.db.engine import init_db
from aividio.web.templating import get_templates  # noqa: F401 — re-exported for back-compat

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Import route modules here (after templating is available) to avoid
    # the circular-import caused by routes importing get_templates from this
    # module before it is fully initialised.
    from aividio.web.routes import (  # noqa: PLC0415
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

    # CORS — allow the frontend origin in production and localhost in dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://aividio.com",
            "https://www.aividio.com",
            "http://localhost:3000",
            "http://localhost:3002",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint (used by Nginx and deploy script)
    @app.get("/health", include_in_schema=False)
    async def health_check():
        return JSONResponse({"status": "ok"})

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
