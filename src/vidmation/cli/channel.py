"""Channel management commands."""

from __future__ import annotations

from pathlib import Path

import typer

from vidmation.cli.theme import (
    console,
    error,
    status_badge,
    styled_table,
    success,
    warning,
)
from vidmation.db.engine import get_session, init_db
from vidmation.db.repos import ChannelRepo

channel_app = typer.Typer(no_args_is_help=True)


# ---------------------------------------------------------------------------
# vidmation channel list
# ---------------------------------------------------------------------------

@channel_app.command("list")
def channel_list(
    all_channels: bool = typer.Option(False, "--all", "-a", help="Include inactive channels."),
) -> None:
    """List all configured channels."""
    init_db()

    session = get_session()
    repo = ChannelRepo(session)
    channels = repo.list_all(active_only=not all_channels)
    session.close()

    if not channels:
        warning("No channels found.  Create one with: [bold]vidmation channel add[/bold]")
        return

    table = styled_table("Channels")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("ID", style="dim", max_width=12)
    table.add_column("Profile Path", style="dim")
    table.add_column("YouTube ID", style="dim")
    table.add_column("Active", justify="center")
    table.add_column("Created", style="dim")

    for ch in channels:
        table.add_row(
            ch.name,
            ch.id[:12] + "...",
            ch.profile_path,
            ch.youtube_channel_id or "-",
            status_badge("active") if ch.is_active else status_badge("inactive"),
            ch.created_at.strftime("%Y-%m-%d %H:%M") if ch.created_at else "-",
        )

    console.print(table)


# ---------------------------------------------------------------------------
# vidmation channel add
# ---------------------------------------------------------------------------

@channel_app.command("add")
def channel_add(
    name: str = typer.Option(..., "--name", "-n", help="Channel name (must be unique)."),
    profile: str = typer.Option(
        "channel_profiles/default.yml",
        "--profile",
        "-p",
        help="Path to the channel profile YAML.",
    ),
) -> None:
    """Register a new channel."""
    init_db()

    # Validate profile exists
    profile_path = Path(profile)
    if not profile_path.exists():
        error(
            f"Profile file not found: {profile}\n"
            f"Create it or use the default: channel_profiles/default.yml"
        )
        raise typer.Exit(1)

    session = get_session()
    repo = ChannelRepo(session)

    # Check uniqueness
    existing = repo.get_by_name(name)
    if existing:
        error(f"Channel '{name}' already exists (ID: {existing.id[:12]}...).")
        session.close()
        raise typer.Exit(1)

    channel = repo.create(name=name, profile_path=str(profile))
    session.close()

    success(f"Channel created: {channel.name}  (ID: [cyan]{channel.id}[/cyan])")


# ---------------------------------------------------------------------------
# vidmation channel auth
# ---------------------------------------------------------------------------

@channel_app.command("auth")
def channel_auth(
    name: str = typer.Argument(help="Channel name to authenticate."),
) -> None:
    """Start the YouTube OAuth flow for a channel.

    This will open a browser window for Google account authorization.
    The resulting token is stored in the channel's database record.
    """
    init_db()

    session = get_session()
    repo = ChannelRepo(session)
    channel = repo.get_by_name(name)

    if channel is None:
        error(f"Channel '{name}' not found.")
        session.close()
        raise typer.Exit(1)

    console.print(f"Starting OAuth flow for channel [cyan]{name}[/cyan]...")

    try:
        from vidmation.services.youtube.auth import get_credentials

        creds = get_credentials(channel_name=name)

        # Store the token JSON in the channel record
        channel.oauth_token_json = creds.to_json() if hasattr(creds, "to_json") else str(creds)
        session.commit()

        success(f"Authentication successful for channel '{name}'!")
    except ImportError:
        error(
            "YouTube auth dependencies not available.  "
            "Ensure google-auth-oauthlib is installed."
        )
        raise typer.Exit(1)
    except Exception as exc:
        error(f"Error during OAuth flow: {exc}")
        raise typer.Exit(1)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# vidmation channel remove (bonus utility)
# ---------------------------------------------------------------------------

@channel_app.command("deactivate")
def channel_deactivate(
    name: str = typer.Argument(help="Channel name to deactivate."),
) -> None:
    """Mark a channel as inactive (soft-delete)."""
    init_db()

    session = get_session()
    repo = ChannelRepo(session)
    channel = repo.get_by_name(name)

    if channel is None:
        error(f"Channel '{name}' not found.")
        session.close()
        raise typer.Exit(1)

    channel.is_active = False
    session.commit()
    session.close()

    success(f"Channel [cyan]{name}[/cyan] deactivated.")
