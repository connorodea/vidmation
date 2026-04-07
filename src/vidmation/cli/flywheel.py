"""Content flywheel commands — repurpose YouTube videos into multi-platform content."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from vidmation.config.settings import get_settings

console = Console()
err_console = Console(stderr=True)

flywheel_app = typer.Typer(no_args_is_help=True)

# All platforms the flywheel can target
# Video export platforms (for reformatting via MultiPlatformExporter)
VIDEO_PLATFORMS = [
    "instagram_reels",
    "tiktok",
    "facebook",
    "twitter",
]

# Copy generation platforms (for AI social media copy via ContentRepurposer)
COPY_PLATFORMS = [
    "instagram_reels",
    "instagram_feed",
    "tiktok",
    "facebook_video",
    "x_thread",
    "x_single",
]

# User-facing platform aliases -> (video_platform, copy_platforms)
PLATFORM_MAP: dict[str, dict[str, list[str] | str | None]] = {
    "instagram_reels": {"video": "instagram_reels", "copy": ["instagram_reels"]},
    "instagram_feed": {"video": None, "copy": ["instagram_feed"]},
    "tiktok": {"video": "tiktok", "copy": ["tiktok"]},
    "facebook": {"video": "facebook", "copy": ["facebook_video"]},
    "twitter": {"video": "twitter", "copy": ["x_thread", "x_single"]},
    "all": {
        "video": ["instagram_reels", "tiktok", "facebook", "twitter"],
        "copy": COPY_PLATFORMS,
    },
}

ALL_PLATFORMS = list(PLATFORM_MAP.keys())


# ---------------------------------------------------------------------------
# vidmation flywheel run
# ---------------------------------------------------------------------------

@flywheel_app.command("run")
def flywheel_run(
    video_path: str = typer.Option(..., "--video", "-v", help="Path to the master YouTube video."),
    script_file: str = typer.Option(..., "--script", "-s", help="Path to the script JSON file."),
    output_dir: str = typer.Option("output/flywheel", "--output", "-o", help="Output directory for all assets."),
    platforms: Optional[str] = typer.Option(
        None, "--platforms", "-p",
        help="Comma-separated platforms (default: all). Options: ig_reels, ig_feed, tiktok, facebook, twitter",
    ),
    skip_video: bool = typer.Option(False, "--skip-video", help="Skip video reformatting, only generate social copy."),
    skip_copy: bool = typer.Option(False, "--skip-copy", help="Skip AI social copy generation, only reformat video."),
) -> None:
    """Run the content flywheel — repurpose a YouTube video into multi-platform content.

    Takes a master video and its script, then:
    1. Generates AI social media copy (captions, threads, hashtags) for each platform
    2. Reformats the video for each platform's specs (resolution, duration, format)
    3. Extracts short clips based on AI-suggested highlight moments
    4. Outputs everything into organized platform folders
    """
    settings = get_settings()
    video_file = Path(video_path)
    script_path = Path(script_file)
    out_dir = Path(output_dir)

    if not video_file.exists():
        err_console.print(f"[red]Error:[/red] Video not found: {video_path}")
        raise typer.Exit(1)
    if not script_path.exists():
        err_console.print(f"[red]Error:[/red] Script not found: {script_file}")
        raise typer.Exit(1)

    script = json.loads(script_path.read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)

    # Resolve platforms
    if platforms:
        user_platforms = [p.strip().lower().replace("-", "_") for p in platforms.split(",")]
    else:
        user_platforms = ["instagram_reels", "instagram_feed", "tiktok", "facebook", "twitter"]

    # Resolve to video and copy platform lists
    video_targets: list[str] = []
    copy_targets: list[str] = []
    for p in user_platforms:
        mapping = PLATFORM_MAP.get(p, {"video": p, "copy": [p]})
        v = mapping.get("video")
        c = mapping.get("copy", [])
        if v:
            if isinstance(v, list):
                video_targets.extend(v)
            else:
                video_targets.append(v)
        if isinstance(c, list):
            copy_targets.extend(c)
    target_platforms = user_platforms

    console.print(Panel.fit(
        f"[bold]Content Flywheel[/bold]\n\n"
        f"  Video:     [cyan]{video_file.name}[/cyan]\n"
        f"  Script:    [cyan]{script_path.name}[/cyan]\n"
        f"  Platforms: {', '.join(target_platforms)}\n"
        f"  Output:    [dim]{out_dir}[/dim]",
        title="Flywheel Starting",
    ))

    results: dict[str, dict] = {}

    # Step 1: Generate AI social media copy
    if not skip_copy:
        console.print("\n[bold]Step 1:[/bold] Generating social media copy with AI...")
        try:
            from vidmation.services.repurpose import create_repurposer
            from vidmation.config.profiles import get_default_profile

            with console.status("[cyan]AI generating platform-specific content...[/cyan]"):
                repurposer = create_repurposer(settings=settings)
                copy_results = repurposer.generate(
                    script=script,
                    platforms=copy_targets,
                    channel_profile=get_default_profile(),
                )

            # Save copy to files
            for platform_name, content in copy_results.items():
                platform_dir = out_dir / platform_name
                platform_dir.mkdir(parents=True, exist_ok=True)
                copy_path = platform_dir / "social_copy.json"
                copy_path.write_text(json.dumps(content, indent=2), encoding="utf-8")
                results.setdefault(platform_name, {})["copy"] = str(copy_path)

                # Also write a human-readable text version
                text_path = platform_dir / "social_copy.txt"
                _write_readable_copy(text_path, platform_name, content)
                results[platform_name]["copy_text"] = str(text_path)

            console.print(f"  [green]Generated copy for {len(copy_results)} platforms[/green]")
        except Exception as exc:
            console.print(f"  [yellow]Warning:[/yellow] AI copy generation failed: {exc}")

    # Step 2: Reformat video for each platform
    if not skip_video:
        console.print("\n[bold]Step 2:[/bold] Reformatting video for each platform...")
        try:
            from vidmation.platforms.exporter import MultiPlatformExporter

            exporter = MultiPlatformExporter(output_dir=out_dir)

            with console.status("[cyan]Reformatting video...[/cyan]"):
                video_results = exporter.export(
                    video_path=video_file,
                    platforms=video_targets,
                )

            for platform_name, path in video_results.items():
                results.setdefault(platform_name, {})["video"] = str(path)
                console.print(f"  [green]{platform_name}:[/green] {path.name}")

        except Exception as exc:
            console.print(f"  [yellow]Warning:[/yellow] Video reformatting failed: {exc}")

    # Step 3: Extract highlight clips
    if not skip_video and not skip_copy:
        console.print("\n[bold]Step 3:[/bold] Extracting highlight clips...")
        clip_count = 0
        for platform_name in target_platforms:
            copy_path = out_dir / platform_name / "social_copy.json"
            if not copy_path.exists():
                continue

            content = json.loads(copy_path.read_text(encoding="utf-8"))
            clips = content.get("clip_suggestions", [])
            if not clips:
                continue

            clips_dir = out_dir / platform_name / "clips"
            clips_dir.mkdir(parents=True, exist_ok=True)

            for idx, clip in enumerate(clips[:5]):
                start = clip.get("start_sec", 0)
                end = clip.get("end_sec", start + 30)
                duration = end - start

                if duration <= 0 or duration > 180:
                    continue

                clip_path = clips_dir / f"clip_{idx + 1}_{start:.0f}s-{end:.0f}s.mp4"
                try:
                    _extract_clip(video_file, clip_path, start, duration)
                    clip_count += 1
                except Exception as exc:
                    console.print(f"  [yellow]Warning:[/yellow] Clip extraction failed: {exc}")

        if clip_count > 0:
            console.print(f"  [green]Extracted {clip_count} highlight clips[/green]")

    # Summary
    console.print()

    # Save manifest
    manifest_path = out_dir / "flywheel_manifest.json"
    manifest = {
        "source_video": str(video_file),
        "source_script": str(script_path),
        "platforms": results,
        "title": script.get("title", ""),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Print summary table
    table = Table(title="Flywheel Results", show_lines=True)
    table.add_column("Platform", style="cyan")
    table.add_column("Video", style="green")
    table.add_column("Copy", style="green")
    table.add_column("Clips", style="green")

    for platform_name in target_platforms:
        data = results.get(platform_name, {})
        clips_dir = out_dir / platform_name / "clips"
        clip_count = len(list(clips_dir.glob("*.mp4"))) if clips_dir.exists() else 0
        table.add_row(
            platform_name,
            "Yes" if "video" in data else "-",
            "Yes" if "copy" in data else "-",
            str(clip_count) if clip_count > 0 else "-",
        )

    console.print(table)
    console.print(f"\nAll assets saved to: [cyan]{out_dir}[/cyan]")
    console.print(f"Manifest: [dim]{manifest_path}[/dim]")


# ---------------------------------------------------------------------------
# vidmation flywheel copy
# ---------------------------------------------------------------------------

@flywheel_app.command("copy")
def flywheel_copy(
    script_file: str = typer.Option(..., "--script", "-s", help="Path to the script JSON file."),
    platforms: Optional[str] = typer.Option(None, "--platforms", "-p", help="Comma-separated platforms."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output JSON file."),
) -> None:
    """Generate social media copy from a script without video processing."""
    settings = get_settings()
    script_path = Path(script_file)

    if not script_path.exists():
        err_console.print(f"[red]Error:[/red] Script not found: {script_file}")
        raise typer.Exit(1)

    script = json.loads(script_path.read_text(encoding="utf-8"))

    # Resolve to copy platform names
    copy_targets: list[str] = []
    if platforms:
        for p in platforms.split(","):
            p = p.strip().lower().replace("-", "_")
            mapping = PLATFORM_MAP.get(p, {"copy": [p]})
            c = mapping.get("copy", [p])
            if isinstance(c, list):
                copy_targets.extend(c)
    else:
        copy_targets = list(COPY_PLATFORMS)

    from vidmation.services.repurpose import create_repurposer
    from vidmation.config.profiles import get_default_profile

    with console.status("[cyan]Generating social media copy...[/cyan]"):
        repurposer = create_repurposer(settings=settings)
        results = repurposer.generate(
            script=script,
            platforms=copy_targets,
            channel_profile=get_default_profile(),
        )

    output_json = json.dumps(results, indent=2)

    if output:
        Path(output).write_text(output_json, encoding="utf-8")
        console.print(f"[green]Social copy saved to {output}[/green]")
    else:
        console.print_json(output_json)


# ---------------------------------------------------------------------------
# vidmation flywheel platforms
# ---------------------------------------------------------------------------

@flywheel_app.command("platforms")
def flywheel_platforms() -> None:
    """List all supported flywheel platforms and their specs."""
    from vidmation.platforms.exporter import MultiPlatformExporter

    exporter = MultiPlatformExporter()
    platforms = exporter.get_supported_platforms()

    table = Table(title="Supported Platforms", show_lines=True)
    table.add_column("Platform", style="cyan")
    table.add_column("Resolution")
    table.add_column("Max Duration")
    table.add_column("Video", justify="center")
    table.add_column("Copy", justify="center")

    platform_info = {
        "youtube": ("1920x1080", "12h", True, True),
        "youtube_shorts": ("1080x1920", "60s", True, True),
        "tiktok": ("1080x1920", "10min", True, True),
        "instagram_reels": ("1080x1920", "90s", True, True),
        "instagram_feed": ("1080x1080", "60s", False, True),
        "instagram_stories": ("1080x1920", "60s", True, True),
        "facebook": ("1920x1080", "240min", True, True),
        "facebook_square": ("1080x1080", "240min", True, True),
        "twitter": ("1280x720", "2min20s", True, True),
    }

    for p in sorted(platform_info.keys()):
        res, dur, has_video, has_copy = platform_info[p]
        table.add_row(
            p,
            res,
            dur,
            "[green]Yes[/green]" if has_video else "[dim]-[/dim]",
            "[green]Yes[/green]" if has_copy else "[dim]-[/dim]",
        )

    console.print(table)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_clip(
    video_path: Path, output_path: Path, start_sec: float, duration: float
) -> Path:
    """Extract a clip from a video using ffmpeg."""
    import ffmpeg

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        (
            ffmpeg
            .input(str(video_path), ss=start_sec, t=duration)
            .output(
                str(output_path),
                vcodec="libx264", acodec="aac",
                crf="20", preset="fast",
                pix_fmt="yuv420p",
            )
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
        raise RuntimeError(f"Clip extraction failed: {stderr}") from exc

    return output_path


def _write_readable_copy(path: Path, platform_name: str, content: dict) -> None:
    """Write a human-readable text version of the social copy."""
    lines: list[str] = [f"=== {platform_name.upper().replace('_', ' ')} ===\n"]

    if "caption" in content:
        lines.append(f"CAPTION:\n{content['caption']}\n")

    if "tweets" in content:
        lines.append("THREAD:")
        for i, tweet in enumerate(content["tweets"], 1):
            lines.append(f"  {i}/ {tweet}")
        lines.append("")

    if "text" in content:
        lines.append(f"POST:\n{content['text']}\n")

    if "title" in content:
        lines.append(f"TITLE: {content['title']}\n")

    if "description" in content:
        lines.append(f"DESCRIPTION:\n{content['description']}\n")

    if "hashtags" in content:
        if isinstance(content["hashtags"], list):
            lines.append(f"HASHTAGS: {' '.join(content['hashtags'])}\n")
        else:
            lines.append(f"HASHTAGS: {content['hashtags']}\n")

    if "carousel_slides" in content:
        lines.append("CAROUSEL SLIDES:")
        for i, slide in enumerate(content["carousel_slides"], 1):
            lines.append(f"  Slide {i}: {slide}")
        lines.append("")

    if "clip_suggestions" in content:
        lines.append("CLIP SUGGESTIONS:")
        for clip in content["clip_suggestions"]:
            start = clip.get("start_sec", 0)
            end = clip.get("end_sec", 0)
            reason = clip.get("reason", "")
            lines.append(f"  {start:.0f}s - {end:.0f}s: {reason}")
        lines.append("")

    if "hook" in content:
        lines.append(f"HOOK: {content['hook']}\n")

    if "music_suggestion" in content:
        lines.append(f"MUSIC: {content['music_suggestion']}\n")

    path.write_text("\n".join(lines), encoding="utf-8")
