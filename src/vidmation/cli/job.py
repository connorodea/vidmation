"""Job management commands — list, inspect, cancel, and retry jobs."""

from __future__ import annotations

from typing import Optional

import typer

from vidmation.cli.theme import (
    console,
    error,
    result_panel,
    status_badge,
    styled_table,
    success,
    warning,
)
from vidmation.db.engine import get_session, init_db
from vidmation.db.repos import JobRepo, VideoRepo
from vidmation.models.job import JobStatus

job_app = typer.Typer(no_args_is_help=True)


# ---------------------------------------------------------------------------
# vidmation job list
# ---------------------------------------------------------------------------

@job_app.command("list")
def job_list(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (queued/running/completed/failed/cancelled)."),
    limit: int = typer.Option(25, "--limit", "-n", help="Maximum number of jobs to show."),
) -> None:
    """Show recent pipeline jobs."""
    init_db()

    session = get_session()
    repo = JobRepo(session)

    filter_status = JobStatus(status) if status else None
    jobs = repo.list_all(status=filter_status, limit=limit)
    session.close()

    if not jobs:
        warning("No jobs found.")
        return

    table = styled_table("Jobs")
    table.add_column("ID", style="dim", max_width=12)
    table.add_column("Type", style="cyan", no_wrap=True)
    table.add_column("Status")
    table.add_column("Stage", no_wrap=True)
    table.add_column("Progress", justify="right")
    table.add_column("Video ID", style="dim", max_width=12)
    table.add_column("Created", style="dim")

    for job in jobs:
        table.add_row(
            job.id[:12] + "...",
            job.job_type.value,
            status_badge(job.status.value),
            job.current_stage or "-",
            f"{job.progress_pct}%",
            job.video_id[:12] + "..." if job.video_id else "-",
            job.created_at.strftime("%Y-%m-%d %H:%M") if job.created_at else "-",
        )

    console.print(table)


# ---------------------------------------------------------------------------
# vidmation job status
# ---------------------------------------------------------------------------

@job_app.command("status")
def job_status(
    job_id: str = typer.Argument(help="Job ID (full or prefix)."),
) -> None:
    """Show detailed status for a specific job."""
    init_db()

    session = get_session()
    job_repo = JobRepo(session)
    job = job_repo.get(job_id)

    if job is None:
        error(f"Job '{job_id}' not found.")
        session.close()
        raise typer.Exit(1)

    # Load related video
    video_repo = VideoRepo(session)
    video = video_repo.get(job.video_id) if job.video_id else None
    session.close()

    badge = status_badge(job.status.value)

    rows = [
        ("Job ID:", job.id),
        ("Type:", job.job_type.value),
        ("Status:", badge),
        ("Current Stage:", job.current_stage or "-"),
        ("Progress:", f"{job.progress_pct}%"),
        ("Resume From:", job.resume_from_stage or "-"),
        ("Created:", str(job.created_at or "-")),
        ("Started:", str(job.started_at or "-")),
        ("Completed:", str(job.completed_at or "-")),
    ]

    if job.error_detail:
        rows.append(("[error]Error:[/error]", job.error_detail))

    if video:
        rows.append(("Video ID:", video.id))
        rows.append(("Topic:", video.topic_prompt))
        rows.append(("Title:", video.title or "-"))
        rows.append(("Video Status:", video.status.value))
        if video.file_path:
            rows.append(("File:", video.file_path))

    console.print(result_panel(f"Job {job.id[:12]}...", rows))


# ---------------------------------------------------------------------------
# vidmation job cancel
# ---------------------------------------------------------------------------

@job_app.command("cancel")
def job_cancel(
    job_id: str = typer.Argument(help="Job ID to cancel."),
) -> None:
    """Cancel a queued job.

    Only QUEUED jobs can be cancelled.  Running jobs will complete their
    current stage before the worker checks for cancellation.
    """
    init_db()

    session = get_session()
    repo = JobRepo(session)
    job = repo.get(job_id)

    if job is None:
        error(f"Job '{job_id}' not found.")
        session.close()
        raise typer.Exit(1)

    if job.status not in (JobStatus.QUEUED, JobStatus.RUNNING):
        error(f"Job is already {job.status.value} — cannot cancel.")
        session.close()
        raise typer.Exit(1)

    job.status = JobStatus.CANCELLED
    session.commit()
    session.close()

    success(f"Job {job_id[:12]}... cancelled.")


# ---------------------------------------------------------------------------
# vidmation job retry
# ---------------------------------------------------------------------------

@job_app.command("retry")
def job_retry(
    job_id: str = typer.Argument(help="Job ID to retry."),
    stage: Optional[str] = typer.Option(
        None, "--from-stage", "-s",
        help="Resume from this stage instead of the failed stage.",
    ),
) -> None:
    """Retry a failed job, optionally from a specific stage.

    Creates a new job that resumes from the failed (or specified) stage.
    """
    init_db()

    from vidmation.queue.tasks import enqueue_retry

    try:
        new_job = enqueue_retry(job_id=job_id, resume_from=stage)
    except ValueError as exc:
        error(str(exc))
        raise typer.Exit(1)

    console.print(result_panel(
        "Retry job created!",
        [
            ("New Job ID:", f"[cyan]{new_job.id}[/cyan]"),
            ("Resume From:", new_job.resume_from_stage or "beginning"),
            ("Track with:", f"[bold]vidmation job status {new_job.id}[/bold]"),
        ],
    ))
