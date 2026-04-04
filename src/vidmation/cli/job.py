"""Job management commands — list, inspect, cancel, and retry jobs."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from vidmation.db.engine import get_session, init_db
from vidmation.db.repos import JobRepo, VideoRepo
from vidmation.models.job import JobStatus

console = Console()
err_console = Console(stderr=True)

job_app = typer.Typer(no_args_is_help=True)

# Status badge colours
_STATUS_STYLES = {
    JobStatus.QUEUED: "[yellow]QUEUED[/yellow]",
    JobStatus.RUNNING: "[blue]RUNNING[/blue]",
    JobStatus.COMPLETED: "[green]COMPLETED[/green]",
    JobStatus.FAILED: "[red]FAILED[/red]",
    JobStatus.CANCELLED: "[dim]CANCELLED[/dim]",
}


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
        console.print("[yellow]No jobs found.[/yellow]")
        return

    table = Table(title="Jobs", show_lines=True)
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
            _STATUS_STYLES.get(job.status, str(job.status.value)),
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
        err_console.print(f"[red]Error:[/red] Job '{job_id}' not found.")
        session.close()
        raise typer.Exit(1)

    # Load related video
    video_repo = VideoRepo(session)
    video = video_repo.get(job.video_id) if job.video_id else None
    session.close()

    status_badge = _STATUS_STYLES.get(job.status, str(job.status.value))

    lines = [
        f"[bold]Job ID:[/bold]        {job.id}",
        f"[bold]Type:[/bold]          {job.job_type.value}",
        f"[bold]Status:[/bold]        {status_badge}",
        f"[bold]Current Stage:[/bold] {job.current_stage or '-'}",
        f"[bold]Progress:[/bold]      {job.progress_pct}%",
        f"[bold]Resume From:[/bold]   {job.resume_from_stage or '-'}",
        "",
        f"[bold]Created:[/bold]       {job.created_at or '-'}",
        f"[bold]Started:[/bold]       {job.started_at or '-'}",
        f"[bold]Completed:[/bold]     {job.completed_at or '-'}",
    ]

    if job.error_detail:
        lines.append("")
        lines.append(f"[bold red]Error:[/bold red]")
        lines.append(f"  {job.error_detail}")

    if video:
        lines.append("")
        lines.append(f"[bold]Video ID:[/bold]     {video.id}")
        lines.append(f"[bold]Topic:[/bold]        {video.topic_prompt}")
        lines.append(f"[bold]Title:[/bold]        {video.title or '-'}")
        lines.append(f"[bold]Video Status:[/bold] {video.status.value}")
        if video.file_path:
            lines.append(f"[bold]File:[/bold]         {video.file_path}")

    console.print(Panel("\n".join(lines), title=f"Job {job.id[:12]}..."))


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
        err_console.print(f"[red]Error:[/red] Job '{job_id}' not found.")
        session.close()
        raise typer.Exit(1)

    if job.status not in (JobStatus.QUEUED, JobStatus.RUNNING):
        err_console.print(
            f"[red]Error:[/red] Job is already {job.status.value} — cannot cancel."
        )
        session.close()
        raise typer.Exit(1)

    job.status = JobStatus.CANCELLED
    session.commit()
    session.close()

    console.print(f"[green]Job {job_id[:12]}... cancelled.[/green]")


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
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    console.print(Panel.fit(
        f"[green]Retry job created![/green]\n\n"
        f"  New Job ID:    [cyan]{new_job.id}[/cyan]\n"
        f"  Resume From:   {new_job.resume_from_stage or 'beginning'}\n\n"
        f"Track with: [bold]vidmation job status {new_job.id}[/bold]",
        title="Retry",
    ))
