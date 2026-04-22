"""Asset management CLI commands — upload, list, and delete custom assets."""

from __future__ import annotations

from pathlib import Path

import typer

from aividio.cli.theme import (
    console,
    error,
    info,
    result_panel,
    status_badge,
    styled_table,
    success,
    warning,
)
from aividio.db.engine import init_db
from aividio.services.assets.manager import UPLOADABLE_TYPES, AssetManager

assets_app = typer.Typer(no_args_is_help=True)


# ---------------------------------------------------------------------------
# aividio assets upload
# ---------------------------------------------------------------------------


@assets_app.command("upload")
def assets_upload(
    file: Path = typer.Option(..., "--file", "-f", help="Path to the asset file."),
    asset_type: str = typer.Option(
        ...,
        "--type",
        "-t",
        help=f"Asset type ({', '.join(sorted(UPLOADABLE_TYPES))}).",
    ),
    name: str = typer.Option(..., "--name", "-n", help="Display name for the asset."),
    tags: str = typer.Option("", "--tags", help="Comma-separated tags for categorisation."),
    public: bool = typer.Option(False, "--public", help="Make this asset visible to all users."),
    user_id: str = typer.Option("", "--user-id", "-u", help="Owner user ID (blank for built-in)."),
) -> None:
    """Upload a custom asset (transition, overlay, SFX, intro, outro, watermark)."""
    init_db()

    if not file.exists():
        error(f"File not found: {file}")
        raise typer.Exit(1)

    if asset_type.lower() not in UPLOADABLE_TYPES:
        error(
            f"Invalid asset type '{asset_type}'.\n"
            f"  Valid types: {', '.join(sorted(UPLOADABLE_TYPES))}"
        )
        raise typer.Exit(1)

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    mgr = AssetManager()
    try:
        asset = mgr.upload(
            file_path=file,
            asset_type=asset_type,
            name=name,
            user_id=user_id or None,
            tags=tag_list,
            is_public=public,
        )

        panel = result_panel(
            "Asset Uploaded",
            [
                ("ID:", asset.id),
                ("Name:", asset.name),
                ("Type:", asset.asset_type.value),
                ("Path:", asset.file_path),
                ("Size:", f"{(asset.file_size or 0) / 1024:.1f} KB"),
                ("MIME:", asset.mime_type or "unknown"),
                ("Duration:", f"{asset.duration:.1f}s" if asset.duration else "N/A"),
                ("Public:", "yes" if asset.is_public else "no"),
                ("Tags:", ", ".join(asset.tags) if asset.tags else "-"),
            ],
        )
        console.print(panel)
    except (FileNotFoundError, ValueError) as exc:
        error(str(exc))
        raise typer.Exit(1)
    finally:
        mgr.close()


# ---------------------------------------------------------------------------
# aividio assets list
# ---------------------------------------------------------------------------


@assets_app.command("list")
def assets_list(
    asset_type: str = typer.Option(None, "--type", "-t", help="Filter by asset type."),
    user_id: str = typer.Option(None, "--user-id", "-u", help="Filter by user ID."),
    all_assets: bool = typer.Option(False, "--all", "-a", help="Include public/built-in assets."),
) -> None:
    """List available custom assets."""
    init_db()

    mgr = AssetManager()
    try:
        assets = mgr.list_assets(
            asset_type=asset_type,
            user_id=user_id,
            include_public=all_assets or user_id is None,
        )
    finally:
        mgr.close()

    if not assets:
        warning("No assets found.  Upload one with: [bold]aividio assets upload --file <path> --type transition --name \"My Transition\"[/bold]")
        return

    table = styled_table("Assets")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("ID", style="dim", max_width=12)
    table.add_column("Type", style="bold")
    table.add_column("Size", justify="right")
    table.add_column("Duration", justify="right")
    table.add_column("Public", justify="center")
    table.add_column("Tags", style="dim")
    table.add_column("Created", style="dim")

    for a in assets:
        size_str = f"{(a.file_size or 0) / 1024:.0f} KB" if a.file_size else "-"
        dur_str = f"{a.duration:.1f}s" if a.duration else "-"
        tags_str = ", ".join(a.tags) if a.tags else "-"
        created_str = a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else "-"

        table.add_row(
            a.name,
            a.id[:12] + "...",
            a.asset_type.value,
            size_str,
            dur_str,
            status_badge("active") if a.is_public else status_badge("inactive"),
            tags_str,
            created_str,
        )

    console.print(table)
    info(f"{len(assets)} asset(s) found")


# ---------------------------------------------------------------------------
# aividio assets delete
# ---------------------------------------------------------------------------


@assets_app.command("delete")
def assets_delete(
    asset_id: str = typer.Argument(help="ID of the asset to delete."),
    force: bool = typer.Option(False, "--force", "-y", help="Skip confirmation prompt."),
) -> None:
    """Delete a custom asset by ID."""
    init_db()

    mgr = AssetManager()
    try:
        asset = mgr.get_asset(asset_id)
        if asset is None:
            error(f"Asset not found: {asset_id}")
            raise typer.Exit(1)

        if not force:
            console.print(f"\n  About to delete: [cyan]{asset.name}[/cyan] ({asset.asset_type.value})")
            console.print(f"  File: [dim]{asset.file_path}[/dim]\n")
            confirm = typer.confirm("  Are you sure?", default=False)
            if not confirm:
                warning("Cancelled.")
                raise typer.Exit(0)

        mgr.delete_asset(asset_id)
        success(f"Asset deleted: {asset.name} ({asset_id[:12]}...)")
    except ValueError as exc:
        error(str(exc))
        raise typer.Exit(1)
    finally:
        mgr.close()


# ---------------------------------------------------------------------------
# aividio assets info
# ---------------------------------------------------------------------------


@assets_app.command("info")
def assets_info(
    asset_id: str = typer.Argument(help="ID of the asset to inspect."),
) -> None:
    """Show detailed information about a single asset."""
    init_db()

    mgr = AssetManager()
    try:
        asset = mgr.get_asset(asset_id)
        if asset is None:
            error(f"Asset not found: {asset_id}")
            raise typer.Exit(1)

        panel = result_panel(
            f"Asset: {asset.name}",
            [
                ("ID:", asset.id),
                ("Type:", asset.asset_type.value),
                ("Source:", asset.source.value if asset.source else "unknown"),
                ("Owner:", asset.user_id or "(built-in)"),
                ("Path:", asset.file_path),
                ("Size:", f"{(asset.file_size or 0) / 1024:.1f} KB"),
                ("MIME:", asset.mime_type or "unknown"),
                ("Duration:", f"{asset.duration:.1f}s" if asset.duration else "N/A"),
                ("Public:", "yes" if asset.is_public else "no"),
                ("Tags:", ", ".join(asset.tags) if asset.tags else "-"),
                ("Created:", asset.created_at.strftime("%Y-%m-%d %H:%M") if asset.created_at else "-"),
                ("Updated:", asset.updated_at.strftime("%Y-%m-%d %H:%M") if asset.updated_at else "-"),
            ],
        )
        console.print(panel)
    finally:
        mgr.close()
