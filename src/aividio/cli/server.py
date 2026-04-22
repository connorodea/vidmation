"""Server and worker commands — launch the web UI and background worker."""

from __future__ import annotations

import threading

import typer

from aividio.cli.theme import (
    LOGO,
    TAGLINE,
    VERSION,
    console,
    header,
    success,
)
from aividio.db.engine import init_db

server_app = typer.Typer(no_args_is_help=True)


# ---------------------------------------------------------------------------
# aividio serve
# ---------------------------------------------------------------------------

@server_app.command("start")
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Bind address."),
    port: int = typer.Option(8000, "--port", "-p", help="Bind port."),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload (development)."),
) -> None:
    """Start the FastAPI web server."""
    import uvicorn

    from aividio.config.settings import get_settings
    from aividio.utils.logging import setup_logging

    setup_logging()
    init_db()

    settings = get_settings()
    bind_host = host or settings.web_host
    bind_port = port or settings.web_port

    console.print(LOGO)
    console.print(TAGLINE)
    console.print(header("Web Server", f"v{VERSION}"))
    console.print()
    success(f"Starting web server at [url]http://{bind_host}:{bind_port}[/url]")

    uvicorn.run(
        "aividio.web.app:app",
        host=bind_host,
        port=bind_port,
        reload=reload,
    )


# ---------------------------------------------------------------------------
# aividio worker
# ---------------------------------------------------------------------------

def worker(
    poll_interval: float = typer.Option(5.0, "--poll", help="Seconds between DB polls."),
    with_web: bool = typer.Option(False, "--with-web", help="Also start the web server."),
    web_host: str = typer.Option("0.0.0.0", "--web-host", help="Web server bind address."),
    web_port: int = typer.Option(8000, "--web-port", help="Web server bind port."),
    with_scheduler: bool = typer.Option(False, "--with-scheduler", help="Also start the schedule checker."),
) -> None:
    """Start the background job worker.

    Use --with-web to also start the FastAPI web server in a thread.
    Use --with-scheduler to enable automatic scheduled video generation.
    """
    from aividio.config.settings import get_settings
    from aividio.queue.worker import JobWorker
    from aividio.utils.logging import setup_logging

    setup_logging()
    init_db()

    settings = get_settings()

    console.print(LOGO)
    console.print(TAGLINE)
    console.print(header("Job Worker", f"v{VERSION}"))
    console.print()

    # Optionally start web server in a background thread
    if with_web:
        _start_web_thread(web_host, web_port)

    # Optionally start scheduler in a background thread
    if with_scheduler:
        _start_scheduler_thread(settings)

    success(f"Starting job worker (poll every {poll_interval}s)")

    job_worker = JobWorker(settings=settings, poll_interval=poll_interval)
    job_worker.run_forever()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _start_web_thread(host: str, port: int) -> threading.Thread:
    """Run uvicorn in a daemon thread."""
    import uvicorn

    def _run():
        uvicorn.run(
            "aividio.web.app:app",
            host=host,
            port=port,
            log_level="warning",
        )

    t = threading.Thread(target=_run, daemon=True, name="web-server")
    t.start()
    success(f"Web server started at [url]http://{host}:{port}[/url] (background thread)")
    return t


def _start_scheduler_thread(settings) -> threading.Thread:
    """Run the video scheduler in a daemon thread."""
    from aividio.queue.scheduler import VideoScheduler

    scheduler = VideoScheduler(settings=settings)
    t = scheduler.run_in_thread()
    success("Scheduler started (background thread)")
    return t
