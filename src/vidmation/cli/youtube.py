"""YouTube management commands — OAuth setup, upload, schedule, list."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import typer

from vidmation.cli.theme import (
    console,
    err,
    error,
    header,
    info,
    kv,
    result_panel,
    spinner,
    status_badge,
    step,
    styled_table,
    success,
    warning,
)
from vidmation.config.settings import get_settings
from vidmation.db.engine import get_session, init_db

youtube_app = typer.Typer(no_args_is_help=True)


# ---------------------------------------------------------------------------
# vidmation youtube setup
# ---------------------------------------------------------------------------

@youtube_app.command("setup")
def youtube_setup() -> None:
    """Set up YouTube API credentials (interactive).

    Guides you through placing the client_secret.json file and
    running the OAuth consent flow.
    """
    settings = get_settings()
    data_dir = settings.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    client_secret_path = data_dir / "client_secret.json"
    token_path = data_dir / "youtube_token.json"

    console.print(header(
        "YouTube API Setup",
        subtitle="Connect VIDMATION to your YouTube channel.\n"
        "You need a Google Cloud project with the YouTube Data API v3 enabled.",
    ))

    # Step 1: Check for client_secret.json
    if client_secret_path.exists():
        success(f"Found client_secret.json at {client_secret_path}")
    else:
        step(1, "Download your OAuth client secret:")
        console.print(
            "  1. Go to [link=https://console.cloud.google.com/apis/credentials]Google Cloud Console[/link]\n"
            "  2. Create or select a project\n"
            "  3. Enable the [bold]YouTube Data API v3[/bold]\n"
            "  4. Create OAuth 2.0 credentials (Desktop application)\n"
            "  5. Download the JSON file\n"
            f"  6. Save it as: [highlight]{client_secret_path}[/highlight]\n"
        )
        console.print("Press Enter after placing the file...", end="")
        input()

        if not client_secret_path.exists():
            error(f"File not found at {client_secret_path}")
            raise typer.Exit(1)

    # Step 2: Run OAuth flow
    if token_path.exists():
        success(f"Found existing token at {token_path}")
        reauth = typer.confirm("Re-authenticate?", default=False)
        if not reauth:
            success("Setup complete! YouTube credentials are ready.")
            return

    step(2, "Authenticating with YouTube...")
    info("A browser window will open for Google sign-in.")

    from vidmation.services.youtube.auth import get_credentials

    try:
        creds = get_credentials(
            token_path=token_path,
            client_secret_path=client_secret_path,
        )
    except Exception as exc:
        error(f"OAuth failed: {exc}")
        raise typer.Exit(1)

    # Step 3: Verify by fetching channel info
    step(3, "Verifying access...")

    try:
        from googleapiclient.discovery import build

        service = build("youtube", "v3", credentials=creds, cache_discovery=False)
        response = service.channels().list(part="snippet", mine=True).execute()
        channels = response.get("items", [])

        if channels:
            ch = channels[0]["snippet"]
            console.print(result_panel(
                "YouTube Setup Complete",
                [
                    ("Channel:", ch["title"]),
                    ("ID:", f"[id]{channels[0]['id']}[/id]"),
                    ("Token:", f"[path]{token_path}[/path]"),
                ],
            ))
        else:
            warning("No channels found for this account.")
    except Exception as exc:
        warning(f"Could not verify channel: {exc}")
        success("Token saved. You can try uploading to verify.")


# ---------------------------------------------------------------------------
# vidmation youtube upload
# ---------------------------------------------------------------------------

@youtube_app.command("upload")
def youtube_upload(
    video_path: str = typer.Option(..., "--video", "-v", help="Path to video file."),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Video title (auto-generated if omitted)."),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Video description."),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated tags."),
    visibility: str = typer.Option("private", "--visibility", help="public, unlisted, or private."),
    thumbnail: Optional[str] = typer.Option(None, "--thumbnail", help="Path to thumbnail image."),
    srt: Optional[str] = typer.Option(None, "--srt", help="Path to SRT caption file to upload."),
    schedule: Optional[str] = typer.Option(None, "--schedule", help="Schedule publish time (ISO 8601 or '+Xh' relative)."),
    category: str = typer.Option("22", "--category", help="YouTube category ID."),
    ai_metadata: bool = typer.Option(False, "--ai-metadata", help="Generate title/description/tags with AI."),
    script_file: Optional[str] = typer.Option(None, "--script-file", help="Script JSON for AI metadata generation."),
) -> None:
    """Upload a video to YouTube with optional AI-generated metadata."""
    settings = get_settings()
    video_file = Path(video_path)

    if not video_file.exists():
        error(f"Video file not found: {video_path}")
        raise typer.Exit(1)

    # Load credentials
    token_path = settings.data_dir / "youtube_token.json"
    client_secret_path = settings.data_dir / "client_secret.json"

    if not token_path.exists():
        error(
            "YouTube not configured. "
            "Run [bold]vidmation youtube setup[/bold] first."
        )
        raise typer.Exit(1)

    from vidmation.services.youtube.auth import get_credentials

    creds = get_credentials(token_path=token_path, client_secret_path=client_secret_path)

    # AI metadata generation
    if ai_metadata:
        script = None
        if script_file:
            script = json.loads(Path(script_file).read_text(encoding="utf-8"))

        if script:
            from vidmation.services.youtube.metadata import YouTubeMetadataGenerator

            with spinner("Generating AI metadata..."):
                meta_gen = YouTubeMetadataGenerator(settings=settings)
                from vidmation.config.profiles import get_default_profile

                metadata = meta_gen.generate(script=script, channel_profile=get_default_profile())

            title = title or metadata.get("title", "")
            description = description or metadata.get("description", "")
            tags = tags or ",".join(metadata.get("tags", []))
            category = metadata.get("category_id", category)

            success(f"AI Title: {title}")
        else:
            warning("--ai-metadata requires --script-file for best results.")

    # Defaults
    title = title or video_file.stem.replace("_", " ").title()
    description = description or ""
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    # Parse schedule
    publish_at = None
    if schedule:
        publish_at = _parse_schedule(schedule)
        visibility = "private"  # Must be private for scheduled publishing
        info(f"Scheduled for: {publish_at.isoformat()}")

    from vidmation.services.youtube.uploader import YouTubeUploader

    uploader = YouTubeUploader(credentials=creds)

    with spinner("Uploading to YouTube..."):
        if publish_at:
            video_id = uploader.upload_with_schedule(
                video_path=video_file,
                title=title,
                description=description,
                tags=tag_list,
                category_id=category,
                thumbnail_path=Path(thumbnail) if thumbnail else None,
                publish_at=publish_at,
            )
        else:
            video_id = uploader.upload(
                video_path=video_file,
                title=title,
                description=description,
                tags=tag_list,
                category_id=category,
                thumbnail_path=Path(thumbnail) if thumbnail else None,
                visibility=visibility,
            )

    rows = [
        ("Video ID:", f"[id]{video_id}[/id]"),
        ("Title:", title),
        ("Status:", status_badge(visibility)),
    ]
    if publish_at:
        rows.append(("Scheduled:", publish_at.isoformat()))
    rows.append(("URL:", f"[url]https://youtube.com/watch?v={video_id}[/url]"))
    console.print(result_panel("Upload Successful", rows))

    # Upload captions if provided
    if srt:
        srt_path = Path(srt)
        if srt_path.exists():
            with spinner("Uploading captions..."):
                uploader.upload_captions(
                    video_id=video_id,
                    srt_path=srt_path,
                    language="en",
                    name="English",
                )
            success("Captions uploaded.")
        else:
            warning(f"SRT file not found: {srt}")


# ---------------------------------------------------------------------------
# vidmation youtube list
# ---------------------------------------------------------------------------

@youtube_app.command("list")
def youtube_list(
    max_results: int = typer.Option(10, "--max", "-n", help="Number of videos to show."),
) -> None:
    """List recent videos on your YouTube channel."""
    settings = get_settings()
    token_path = settings.data_dir / "youtube_token.json"
    client_secret_path = settings.data_dir / "client_secret.json"

    if not token_path.exists():
        error("Run [bold]vidmation youtube setup[/bold] first.")
        raise typer.Exit(1)

    from vidmation.services.youtube.auth import get_credentials
    from vidmation.services.youtube.uploader import YouTubeUploader

    creds = get_credentials(token_path=token_path, client_secret_path=client_secret_path)
    uploader = YouTubeUploader(credentials=creds)

    with spinner("Fetching videos..."):
        videos = uploader.list_channel_videos(max_results=max_results)

    if not videos:
        warning("No videos found on your channel.")
        return

    table = styled_table("Your YouTube Videos", show_lines=True)
    table.add_column("Title", style="highlight", max_width=50)
    table.add_column("ID", style="id", max_width=15)
    table.add_column("Published", style="muted")
    table.add_column("Views", justify="right")
    table.add_column("Status")

    for v in videos:
        table.add_row(
            v.get("title", "N/A"),
            v.get("id", ""),
            v.get("published_at", "")[:10],
            str(v.get("view_count", 0)),
            status_badge(v.get("privacy", "unknown")),
        )

    console.print(table)


# ---------------------------------------------------------------------------
# vidmation youtube status
# ---------------------------------------------------------------------------

@youtube_app.command("status")
def youtube_status(
    video_id: str = typer.Argument(help="YouTube video ID to check."),
) -> None:
    """Get detailed status of a YouTube video."""
    settings = get_settings()
    token_path = settings.data_dir / "youtube_token.json"
    client_secret_path = settings.data_dir / "client_secret.json"

    if not token_path.exists():
        error("Run [bold]vidmation youtube setup[/bold] first.")
        raise typer.Exit(1)

    from vidmation.services.youtube.auth import get_credentials
    from vidmation.services.youtube.uploader import YouTubeUploader

    creds = get_credentials(token_path=token_path, client_secret_path=client_secret_path)
    uploader = YouTubeUploader(credentials=creds)

    with spinner("Fetching video details..."):
        details = uploader.get_video_details(video_id)

    if not details:
        error(f"Video '{video_id}' not found.")
        raise typer.Exit(1)

    snippet = details.get("snippet", {})
    stats = details.get("statistics", {})
    vid_status = details.get("status", {})
    privacy = vid_status.get("privacyStatus", "unknown")

    console.print(result_panel(
        snippet.get("title", "N/A"),
        [
            ("Video ID:", f"[id]{video_id}[/id]"),
            ("Channel:", snippet.get("channelTitle", "N/A")),
            ("Published:", snippet.get("publishedAt", "N/A")),
            ("Privacy:", status_badge(privacy)),
            ("Views:", stats.get("viewCount", "0")),
            ("Likes:", stats.get("likeCount", "0")),
            ("Comments:", stats.get("commentCount", "0")),
            ("Description:", f"{snippet.get('description', '')[:200]}..."),
        ],
    ))


# ---------------------------------------------------------------------------
# vidmation youtube update
# ---------------------------------------------------------------------------

@youtube_app.command("update")
def youtube_update(
    video_id: str = typer.Argument(help="YouTube video ID to update."),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="New title."),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="New description."),
    tags: Optional[str] = typer.Option(None, "--tags", help="New comma-separated tags."),
) -> None:
    """Update metadata on an existing YouTube video."""
    if not title and not description and not tags:
        error("Provide at least one of --title, --description, or --tags.")
        raise typer.Exit(1)

    settings = get_settings()
    token_path = settings.data_dir / "youtube_token.json"
    client_secret_path = settings.data_dir / "client_secret.json"

    from vidmation.services.youtube.auth import get_credentials
    from vidmation.services.youtube.uploader import YouTubeUploader

    creds = get_credentials(token_path=token_path, client_secret_path=client_secret_path)
    uploader = YouTubeUploader(credentials=creds)

    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    with spinner("Updating video..."):
        uploader.update_video_metadata(
            video_id=video_id,
            title=title,
            description=description,
            tags=tag_list,
        )

    success(f"Video {video_id} updated successfully.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_schedule(schedule_str: str) -> datetime:
    """Parse a schedule string into a UTC datetime.

    Supports:
    - ISO 8601: "2026-04-10T14:00:00Z"
    - Relative: "+2h", "+30m", "+1d"
    """
    schedule_str = schedule_str.strip()

    if schedule_str.startswith("+"):
        amount_str = schedule_str[1:]
        unit = amount_str[-1].lower()
        amount = int(amount_str[:-1])

        now = datetime.now(timezone.utc)
        if unit == "h":
            return now + timedelta(hours=amount)
        if unit == "m":
            return now + timedelta(minutes=amount)
        if unit == "d":
            return now + timedelta(days=amount)
        raise ValueError(f"Unknown time unit '{unit}'. Use h (hours), m (minutes), d (days).")

    # Try ISO 8601
    try:
        dt = datetime.fromisoformat(schedule_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        raise ValueError(
            f"Cannot parse schedule '{schedule_str}'. "
            "Use ISO 8601 (2026-04-10T14:00:00Z) or relative (+2h, +30m, +1d)."
        )
