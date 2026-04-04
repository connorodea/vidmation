"""Generate commands — create videos, scripts, voiceovers, and thumbnails."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from vidmation.config.profiles import ChannelProfile, get_default_profile, load_profile
from vidmation.config.settings import get_settings
from vidmation.db.engine import init_db
from vidmation.models.video import VideoFormat

console = Console()
err_console = Console(stderr=True)

generate_app = typer.Typer(no_args_is_help=True)


# ---------------------------------------------------------------------------
# vidmation generate video
# ---------------------------------------------------------------------------

@generate_app.command("video")
def generate_video(
    topic: str = typer.Option(..., "--topic", "-t", help="Video topic / prompt."),
    channel: str = typer.Option("default", "--channel", "-c", help="Channel name."),
    format: str = typer.Option("landscape", "--format", "-f", help="Video format: landscape, portrait, short."),
    no_upload: bool = typer.Option(False, "--no-upload", help="Skip YouTube upload stage."),
    run_async: bool = typer.Option(False, "--async", help="Queue the job instead of running synchronously."),
) -> None:
    """Generate a full video from a topic prompt.

    By default, runs the full pipeline synchronously with live progress.
    Use --async to queue a job for the background worker instead.
    """
    from vidmation.utils.logging import setup_logging

    setup_logging()
    init_db()

    video_format = VideoFormat(format)

    if run_async:
        _generate_video_async(topic, channel, video_format)
    else:
        _generate_video_sync(topic, channel, video_format, no_upload=no_upload)


def _generate_video_async(topic: str, channel: str, video_format: VideoFormat) -> None:
    """Enqueue a video generation job."""
    from vidmation.queue.tasks import enqueue_video

    try:
        video, job = enqueue_video(
            topic=topic,
            channel_name=channel,
            format=video_format,
        )
    except ValueError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    console.print(Panel.fit(
        f"[green]Job queued successfully![/green]\n\n"
        f"  Video ID: [cyan]{video.id}[/cyan]\n"
        f"  Job ID:   [cyan]{job.id}[/cyan]\n\n"
        f"Track progress with: [bold]vidmation job status {job.id}[/bold]",
        title="Queued",
    ))


def _generate_video_sync(
    topic: str,
    channel: str,
    video_format: VideoFormat,
    *,
    no_upload: bool,
) -> None:
    """Run the full pipeline synchronously with Rich progress output."""
    import uuid

    from vidmation.db.engine import get_session
    from vidmation.db.repos import ChannelRepo
    from vidmation.pipeline.context import PipelineContext
    from vidmation.pipeline.orchestrator import PipelineOrchestrator
    from vidmation.pipeline.stages import STAGE_REGISTRY
    from vidmation.utils.files import get_work_dir

    settings = get_settings()
    session = get_session()

    # Resolve channel
    channel_repo = ChannelRepo(session)
    ch = channel_repo.get_by_name(channel)
    if ch is None:
        err_console.print(
            f"[red]Error:[/red] Channel '{channel}' not found.  "
            f"Create it with: [bold]vidmation channel add --name '{channel}'[/bold]"
        )
        session.close()
        raise typer.Exit(1)

    # Load profile
    try:
        profile = load_profile(ch.profile_path)
    except FileNotFoundError:
        profile = get_default_profile()

    video_id = str(uuid.uuid4())
    work_dir = get_work_dir(video_id)

    ctx = PipelineContext(
        video_id=video_id,
        channel_profile=profile,
        topic=topic,
        format=video_format,
        work_dir=work_dir,
    )

    # Optionally exclude upload
    stages = list(STAGE_REGISTRY)
    if no_upload:
        stages = [(n, fn) for n, fn in stages if n != "upload"]

    orchestrator = PipelineOrchestrator(stages=stages, settings=settings)

    console.print(Panel.fit(
        f"[bold]Topic:[/bold] {topic}\n"
        f"[bold]Channel:[/bold] {channel}\n"
        f"[bold]Format:[/bold] {video_format.value}\n"
        f"[bold]Video ID:[/bold] {video_id}\n"
        f"[bold]Stages:[/bold] {len(stages)}",
        title="Pipeline Starting",
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Running pipeline...", total=len(stages))

        # Monkey-patch orchestrator to update progress
        original_run = orchestrator.run

        def tracked_run(context, **kwargs):
            """Wrap the orchestrator to update Rich progress per stage."""
            total_stages = len(orchestrator.stages)
            for idx, (name, stage_fn) in enumerate(orchestrator.stages, 1):
                context.current_stage = name
                progress.update(task, description=f"[cyan]{name}[/cyan]")

                try:
                    stage_fn(context, orchestrator.settings)
                except Exception as exc:
                    progress.update(task, description=f"[red]FAILED: {name}[/red]")
                    err_console.print(f"\n[red]Pipeline failed at stage '{name}':[/red] {exc}")
                    context.save()
                    raise typer.Exit(1)

                context.completed_stages.append(name)
                context.save()
                progress.advance(task)

            return context

        tracked_run(ctx)

    session.close()

    console.print()
    console.print(Panel.fit(
        f"[green]Pipeline completed![/green]\n\n"
        f"  Video ID:   [cyan]{ctx.video_id}[/cyan]\n"
        f"  Title:      {ctx.script.get('title', 'N/A') if ctx.script else 'N/A'}\n"
        f"  Video Path: [dim]{ctx.final_video_path or 'N/A'}[/dim]\n"
        f"  Thumbnail:  [dim]{ctx.thumbnail_path or 'N/A'}[/dim]",
        title="Complete",
    ))


# ---------------------------------------------------------------------------
# vidmation generate script
# ---------------------------------------------------------------------------

@generate_app.command("script")
def generate_script(
    topic: str = typer.Option(..., "--topic", "-t", help="Video topic / prompt."),
    channel: str = typer.Option("default", "--channel", "-c", help="Channel name for profile."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path (default: stdout)."),
) -> None:
    """Generate a script only and output JSON."""
    from vidmation.utils.logging import setup_logging

    setup_logging()
    init_db()

    settings = get_settings()
    profile = _resolve_profile(channel)

    from vidmation.services.scriptgen import create_script_generator

    with console.status("[cyan]Generating script...[/cyan]"):
        generator = create_script_generator(settings=settings)
        script = generator.generate(topic=topic, profile=profile)

    script_json = json.dumps(script, indent=2)

    if output:
        Path(output).write_text(script_json, encoding="utf-8")
        console.print(f"[green]Script saved to {output}[/green]")
    else:
        console.print_json(script_json)


# ---------------------------------------------------------------------------
# vidmation generate voiceover
# ---------------------------------------------------------------------------

@generate_app.command("voiceover")
def generate_voiceover(
    script_file: str = typer.Option(..., "--script-file", "-s", help="Path to script JSON file."),
    channel: str = typer.Option("default", "--channel", "-c", help="Channel name for voice config."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output audio file path."),
) -> None:
    """Generate a voiceover from an existing script file."""
    from vidmation.utils.logging import setup_logging

    setup_logging()
    init_db()

    script_path = Path(script_file)
    if not script_path.exists():
        err_console.print(f"[red]Error:[/red] Script file not found: {script_file}")
        raise typer.Exit(1)

    script = json.loads(script_path.read_text(encoding="utf-8"))
    settings = get_settings()
    profile = _resolve_profile(channel)

    from vidmation.services.tts import create_tts_provider

    # Build narration text
    parts: list[str] = []
    if script.get("hook"):
        parts.append(script["hook"])
    for section in script.get("sections", []):
        parts.append(section["narration"])
    if script.get("outro"):
        parts.append(script["outro"])

    full_narration = "\n\n".join(parts)
    output_path = Path(output) if output else Path("voiceover.mp3")

    with console.status("[cyan]Synthesising voiceover...[/cyan]"):
        tts = create_tts_provider(settings=settings)
        result = tts.synthesize(
            text=full_narration,
            output_path=output_path,
            voice_config=profile.voice,
        )

    console.print(
        f"[green]Voiceover saved to {result['path']}[/green] "
        f"({result.get('duration', 0):.1f}s)"
    )


# ---------------------------------------------------------------------------
# vidmation generate thumbnail
# ---------------------------------------------------------------------------

@generate_app.command("thumbnail")
def generate_thumbnail(
    video_id: str = typer.Option(..., "--video-id", "-v", help="Video ID to generate thumbnail for."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output image path."),
) -> None:
    """Generate a thumbnail for an existing video."""
    from vidmation.utils.logging import setup_logging

    setup_logging()
    init_db()

    from vidmation.db.engine import get_session
    from vidmation.db.repos import ChannelRepo, VideoRepo

    settings = get_settings()
    session = get_session()

    video_repo = VideoRepo(session)
    video = video_repo.get(video_id)
    if video is None:
        err_console.print(f"[red]Error:[/red] Video '{video_id}' not found.")
        session.close()
        raise typer.Exit(1)

    channel_repo = ChannelRepo(session)
    ch = channel_repo.get(video.channel_id)
    profile = _resolve_profile_from_channel(ch)

    script = video.script_json or {}
    title = script.get("title", video.topic_prompt)

    from vidmation.services.imagegen import create_image_generator

    output_path = Path(output) if output else Path(f"thumbnail_{video_id[:8]}.png")

    with console.status("[cyan]Generating thumbnail...[/cyan]"):
        generator = create_image_generator(settings=settings)
        result = generator.generate(
            prompt=f"YouTube thumbnail for: {title}. Style: {profile.thumbnail.style}",
            output_path=output_path,
        )

    # Update video record
    video_repo.update_status(video_id, video.status, thumbnail_path=str(result["path"]))
    session.close()

    console.print(f"[green]Thumbnail saved to {result['path']}[/green]")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_profile(channel_name: str) -> ChannelProfile:
    """Load the channel profile by channel name, falling back to defaults."""
    from vidmation.db.engine import get_session
    from vidmation.db.repos import ChannelRepo

    session = get_session()
    try:
        channel_repo = ChannelRepo(session)
        ch = channel_repo.get_by_name(channel_name)
        return _resolve_profile_from_channel(ch)
    finally:
        session.close()


def _resolve_profile_from_channel(channel) -> ChannelProfile:
    """Load the profile from a channel record, with default fallback."""
    if channel is None:
        return get_default_profile()
    try:
        return load_profile(channel.profile_path)
    except FileNotFoundError:
        return get_default_profile()
