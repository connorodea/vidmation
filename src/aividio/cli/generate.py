"""Generate commands — create videos, scripts, voiceovers, and thumbnails."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from aividio.cli.theme import (
    console,
    error,
    header,
    kv,
    pipeline_progress,
    result_panel,
    spinner,
    styled_table,
    success,
    warning,
)
from aividio.config.profiles import ChannelProfile, get_default_profile, load_profile
from aividio.config.settings import get_settings
from aividio.db.engine import init_db
from aividio.models.video import VideoFormat

generate_app = typer.Typer(no_args_is_help=True)


# ---------------------------------------------------------------------------
# aividio generate styles  (list available video style templates)
# ---------------------------------------------------------------------------

@generate_app.command("styles")
def list_style_templates() -> None:
    """List all built-in video style templates.

    Each template defines a complete visual identity: caption style,
    transitions, music genre, thumbnail style, accent colour, and title
    placement.  Use ``--style <slug>`` with ``aividio generate video``
    to apply a template.
    """
    from aividio.styles.registry import list_templates

    templates = list_templates()

    if not templates:
        warning("No video style templates found.")
        raise typer.Exit()

    console.print(header("Video Style Templates"))
    console.print()

    table = styled_table()
    table.add_column("Slug", style="bold bright_green", no_wrap=True)
    table.add_column("Name", style="bold white")
    table.add_column("Transition", style="dim")
    table.add_column("Music", style="dim")
    table.add_column("Accent", style="dim")
    table.add_column("Description")

    for t in templates:
        # Show the accent colour as a coloured block if possible
        accent = t["color_accent"]
        table.add_row(
            t["slug"],
            t["name"],
            t["transition"],
            t["music_genre"],
            f"[{accent}]{accent}[/{accent}]",
            t["description"],
        )

    console.print(table)
    console.print()
    console.print(
        "  [dim]Tip:[/dim] Use [bold bright_green]aividio generate video "
        "--topic \"...\" --style <slug>[/bold bright_green] to apply a template."
    )
    console.print()


# ---------------------------------------------------------------------------
# aividio generate video
# ---------------------------------------------------------------------------

@generate_app.command("video")
def generate_video(
    topic: str = typer.Option(..., "--topic", "-t", help="Video topic / prompt."),
    channel: str = typer.Option("default", "--channel", "-c", help="Channel name."),
    style: Optional[str] = typer.Option(None, "--style", "-s", help="Video style template slug (e.g. dark-cinematic). Run 'aividio generate styles' to list."),
    format: str = typer.Option("landscape", "--format", "-f", help="Video format: landscape, portrait, short."),
    no_upload: bool = typer.Option(False, "--no-upload", help="Skip YouTube upload stage."),
    run_async: bool = typer.Option(False, "--async", help="Queue the job instead of running synchronously."),
) -> None:
    """Generate a full video from a topic prompt.

    By default, runs the full pipeline synchronously with live progress.
    Use --async to queue a job for the background worker instead.

    Use --style / -s to apply a built-in video style template that controls
    captions, transitions, music genre, thumbnail style, and colour accent.
    Run ``aividio generate styles`` to see all available templates.
    """
    from aividio.utils.logging import setup_logging

    setup_logging()
    init_db()

    video_format = VideoFormat(format)

    if run_async:
        _generate_video_async(topic, channel, video_format, style_slug=style)
    else:
        _generate_video_sync(topic, channel, video_format, no_upload=no_upload, style_slug=style)


def _generate_video_async(
    topic: str,
    channel: str,
    video_format: VideoFormat,
    *,
    style_slug: str | None = None,
) -> None:
    """Enqueue a video generation job."""
    from aividio.queue.tasks import enqueue_video

    if style_slug:
        from aividio.styles.registry import get_template
        try:
            get_template(style_slug)  # validate slug exists
        except ValueError as exc:
            error(str(exc))
            raise typer.Exit(1)

    try:
        video, job = enqueue_video(
            topic=topic,
            channel_name=channel,
            format=video_format,
        )
    except ValueError as exc:
        error(str(exc))
        raise typer.Exit(1)

    rows = [
        ("Video ID:", f"[id]{video.id}[/id]"),
        ("Job ID:", f"[id]{job.id}[/id]"),
        ("Track:", f"[bold]aividio job status {job.id}[/bold]"),
    ]
    if style_slug:
        rows.insert(0, ("Style:", f"[accent]{style_slug}[/accent]"))

    console.print(result_panel("Job queued successfully!", rows))


def _generate_video_sync(
    topic: str,
    channel: str,
    video_format: VideoFormat,
    *,
    no_upload: bool,
    style_slug: str | None = None,
) -> None:
    """Run the full pipeline synchronously with Rich progress output."""
    import uuid

    from aividio.db.engine import get_session
    from aividio.db.repos import ChannelRepo
    from aividio.pipeline.context import PipelineContext
    from aividio.pipeline.orchestrator import PipelineOrchestrator
    from aividio.pipeline.stages import STAGE_REGISTRY
    from aividio.utils.files import get_work_dir

    settings = get_settings()
    session = get_session()

    # Resolve channel
    channel_repo = ChannelRepo(session)
    ch = channel_repo.get_by_name(channel)
    if ch is None:
        error(
            f"Channel '{channel}' not found.  "
            f"Create it with: [bold]aividio channel add --name '{channel}'[/bold]"
        )
        session.close()
        raise typer.Exit(1)

    # Load profile
    try:
        profile = load_profile(ch.profile_path)
    except FileNotFoundError:
        profile = get_default_profile()

    # Apply video style template if provided
    if style_slug:
        from aividio.styles.registry import apply_template

        try:
            profile = apply_template(profile, style_slug)
        except ValueError as exc:
            error(str(exc))
            session.close()
            raise typer.Exit(1)

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

    console.print(header("Pipeline Starting"))
    kv("Topic:", topic)
    kv("Channel:", channel)
    if style_slug:
        kv("Style:", f"[accent]{style_slug}[/accent]")
    kv("Format:", video_format.value)
    kv("Video ID:", f"[id]{video_id}[/id]")
    kv("Stages:", str(len(stages)))
    console.print()

    with pipeline_progress() as progress:
        task = progress.add_task("Running pipeline...", total=len(stages))

        # Monkey-patch orchestrator to update progress
        original_run = orchestrator.run

        def tracked_run(context, **kwargs):
            """Wrap the orchestrator to update Rich progress per stage."""
            total_stages = len(orchestrator.stages)
            for idx, (name, stage_fn) in enumerate(orchestrator.stages, 1):
                context.current_stage = name
                progress.update(task, description=f"[accent]{name}[/accent]")

                try:
                    stage_fn(context, orchestrator.settings)
                except Exception as exc:
                    progress.update(task, description=f"[error]FAILED: {name}[/error]")
                    error(f"Pipeline failed at stage '{name}': {exc}")
                    context.save()
                    raise typer.Exit(1)

                context.completed_stages.append(name)
                context.save()
                progress.advance(task)

            return context

        tracked_run(ctx)

    session.close()

    console.print()
    console.print(result_panel(
        "Pipeline completed!",
        [
            ("Video ID:", f"[id]{ctx.video_id}[/id]"),
            ("Title:", ctx.script.get("title", "N/A") if ctx.script else "N/A"),
            ("Video Path:", f"[path]{ctx.final_video_path or 'N/A'}[/path]"),
            ("Thumbnail:", f"[path]{ctx.thumbnail_path or 'N/A'}[/path]"),
        ],
    ))


# ---------------------------------------------------------------------------
# aividio generate script
# ---------------------------------------------------------------------------

@generate_app.command("script")
def generate_script(
    topic: str = typer.Option(..., "--topic", "-t", help="Video topic / prompt."),
    channel: str = typer.Option("default", "--channel", "-c", help="Channel name for profile."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path (default: stdout)."),
) -> None:
    """Generate a script only and output JSON."""
    from aividio.utils.logging import setup_logging

    setup_logging()
    init_db()

    settings = get_settings()
    profile = _resolve_profile(channel)

    from aividio.services.scriptgen import create_script_generator

    with spinner("Generating script..."):
        generator = create_script_generator(settings=settings)
        script = generator.generate(topic=topic, profile=profile)

    script_json = json.dumps(script, indent=2)

    if output:
        Path(output).write_text(script_json, encoding="utf-8")
        success(f"Script saved to [path]{output}[/path]")
    else:
        console.print_json(script_json)


# ---------------------------------------------------------------------------
# aividio generate voiceover
# ---------------------------------------------------------------------------

@generate_app.command("voiceover")
def generate_voiceover(
    script_file: str = typer.Option(..., "--script-file", "-s", help="Path to script JSON file."),
    channel: str = typer.Option("default", "--channel", "-c", help="Channel name for voice config."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output audio file path."),
) -> None:
    """Generate a voiceover from an existing script file."""
    from aividio.utils.logging import setup_logging

    setup_logging()
    init_db()

    script_path = Path(script_file)
    if not script_path.exists():
        error(f"Script file not found: {script_file}")
        raise typer.Exit(1)

    script = json.loads(script_path.read_text(encoding="utf-8"))
    settings = get_settings()
    profile = _resolve_profile(channel)

    from aividio.services.tts import create_tts_provider

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

    with spinner("Synthesising voiceover..."):
        tts = create_tts_provider(settings=settings)
        audio_path, duration = tts.synthesize(
            text=full_narration,
            output_path=output_path,
            voice_config=profile.voice,
        )

    success(f"Voiceover saved to [path]{audio_path}[/path] ({duration:.1f}s)")


# ---------------------------------------------------------------------------
# aividio generate thumbnail
# ---------------------------------------------------------------------------

@generate_app.command("thumbnail")
def generate_thumbnail(
    video_id: str = typer.Option(..., "--video-id", "-v", help="Video ID to generate thumbnail for."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output image path."),
) -> None:
    """Generate a thumbnail for an existing video."""
    from aividio.utils.logging import setup_logging

    setup_logging()
    init_db()

    from aividio.db.engine import get_session
    from aividio.db.repos import ChannelRepo, VideoRepo

    settings = get_settings()
    session = get_session()

    video_repo = VideoRepo(session)
    video = video_repo.get(video_id)
    if video is None:
        error(f"Video '{video_id}' not found.")
        session.close()
        raise typer.Exit(1)

    channel_repo = ChannelRepo(session)
    ch = channel_repo.get(video.channel_id)
    profile = _resolve_profile_from_channel(ch)

    script = video.script_json or {}
    title = script.get("title", video.topic_prompt)

    from aividio.services.imagegen import create_image_generator

    output_path = Path(output) if output else Path(f"thumbnail_{video_id[:8]}.png")

    with spinner("Generating thumbnail..."):
        generator = create_image_generator(settings=settings)
        saved_path = generator.generate(
            prompt=f"YouTube thumbnail for: {title}. Style: {profile.thumbnail.style}",
            output_path=output_path,
        )

    # Update video record
    video_repo.update_status(video_id, video.status, thumbnail_path=str(saved_path))
    session.close()

    success(f"Thumbnail saved to [path]{saved_path}[/path]")


# ---------------------------------------------------------------------------
# aividio generate blog
# ---------------------------------------------------------------------------

@generate_app.command("blog")
def generate_from_blog(
    url: str = typer.Option(..., "--url", "-u", help="Blog post URL to convert into a video."),
    channel: str = typer.Option("default", "--channel", "-c", help="Channel name for profile."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output script JSON file path."),
    full_video: bool = typer.Option(False, "--video", help="Generate the full video (not just the script)."),
    no_upload: bool = typer.Option(True, "--no-upload", help="Skip YouTube upload."),
) -> None:
    """Convert a blog post URL into a video script (and optionally a full video).

    The AI agent scrapes the blog, analyses the content, and generates
    a structured video script optimised for YouTube.

    Example:
        aividio generate blog --url https://example.com/my-post
        aividio generate blog --url https://example.com/my-post --video
    """
    from aividio.utils.logging import setup_logging

    setup_logging()
    init_db()

    settings = get_settings()
    profile = _resolve_profile(channel)

    # Step 1: Scrape and convert blog to script
    from aividio.services.blog2video import create_blog_converter

    with spinner("Scraping blog and generating script..."):
        converter = create_blog_converter(settings=settings)
        script = converter.convert(url=url, channel_profile=profile)

    console.print(result_panel(
        "Blog converted!",
        [
            ("Source:", f"[url]{url}[/url]"),
            ("Title:", f"[bold]{script.get('title', 'N/A')}[/bold]"),
            ("Sections:", str(len(script.get("sections", [])))),
            ("Duration:", f"~{script.get('total_estimated_duration_seconds', 0)}s"),
        ],
    ))

    # Save script
    script_json = json.dumps(script, indent=2)
    if output:
        Path(output).write_text(script_json, encoding="utf-8")
        success(f"Script saved to [path]{output}[/path]")
    else:
        script_output = Path(f"output/blog_script_{script.get('title', 'untitled')[:30].replace(' ', '_')}.json")
        script_output.parent.mkdir(parents=True, exist_ok=True)
        script_output.write_text(script_json, encoding="utf-8")
        success(f"Script saved to [path]{script_output}[/path]")

    # Optionally run full video pipeline
    if full_video:
        console.print("\n[bold]Generating full video from blog script...[/bold]")

        import uuid

        from aividio.models.video import VideoFormat
        from aividio.pipeline.context import PipelineContext
        from aividio.pipeline.orchestrator import PipelineOrchestrator
        from aividio.pipeline.stages import STAGE_REGISTRY
        from aividio.utils.files import get_work_dir

        video_id = str(uuid.uuid4())
        work_dir = get_work_dir(video_id)

        # Save script to work dir
        (work_dir / "script.json").write_text(script_json, encoding="utf-8")

        ctx = PipelineContext(
            video_id=video_id,
            channel_profile=profile,
            topic=script.get("title", url),
            format=VideoFormat("landscape"),
            work_dir=work_dir,
        )
        # Pre-populate the script so pipeline skips script generation
        ctx.script = script
        ctx.completed_stages.append("script_generation")

        # Build stage list, skipping script gen (already done)
        stages = [(n, fn) for n, fn in STAGE_REGISTRY if n != "script_generation"]
        if no_upload:
            stages = [(n, fn) for n, fn in stages if n != "upload"]

        orchestrator = PipelineOrchestrator(stages=stages, settings=settings)

        with pipeline_progress() as progress:
            task = progress.add_task("Running pipeline...", total=len(stages))

            for name, stage_fn in stages:
                ctx.current_stage = name
                progress.update(task, description=f"[accent]{name}[/accent]")

                try:
                    stage_fn(ctx, settings)
                except Exception as exc:
                    progress.update(task, description=f"[error]FAILED: {name}[/error]")
                    error(f"Pipeline failed at '{name}': {exc}")
                    ctx.save()
                    raise typer.Exit(1)

                ctx.completed_stages.append(name)
                ctx.save()
                progress.advance(task)

        console.print(result_panel(
            "Blog \u2192 Video complete!",
            [
                ("Source:", f"[url]{url}[/url]"),
                ("Title:", script.get("title", "N/A")),
                ("Video:", f"[path]{ctx.final_video_path or 'N/A'}[/path]"),
                ("Thumbnail:", f"[path]{ctx.thumbnail_path or 'N/A'}[/path]"),
            ],
        ))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_profile(channel_name: str) -> ChannelProfile:
    """Load the channel profile by channel name, falling back to defaults."""
    from aividio.db.engine import get_session
    from aividio.db.repos import ChannelRepo

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
