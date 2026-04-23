"""Main Typer application — entry point for the ``aividio`` CLI."""

from __future__ import annotations

import typer

from aividio.cli.agent import agent_app
from aividio.cli.audio import audio_app
from aividio.cli.batch import batch_app
from aividio.cli.channel import channel_app
from aividio.cli.content import content_app
from aividio.cli.effects import effects_app
from aividio.cli.flywheel import flywheel_app
from aividio.cli.generate import generate_app
from aividio.cli.job import job_app
from aividio.cli.server import server_app
from aividio.cli.youtube import youtube_app

app = typer.Typer(
    name="aividio",
    help="AI-powered faceless YouTube video automation platform.",
    no_args_is_help=False,
    invoke_without_command=True,
    rich_markup_mode="rich",
)

# Register sub-command groups — icons help scanability
app.add_typer(generate_app, name="generate", help="[bold bright_green]\u25b6[/] Generate videos, scripts, voiceovers, thumbnails, blog\u2192video.")
app.add_typer(youtube_app, name="youtube", help="[bold red]\u25b6[/] YouTube: setup OAuth, upload, schedule, list, update.")
app.add_typer(flywheel_app, name="flywheel", help="[bold bright_cyan]\u25b6[/] Content flywheel: repurpose for IG, TikTok, FB, X.")
app.add_typer(channel_app, name="channel", help="[bold yellow]\u25b6[/] Manage channel profiles and YouTube connections.")
app.add_typer(job_app, name="job", help="[bold blue]\u25b6[/] View and manage pipeline jobs.")
app.add_typer(batch_app, name="batch", help="[bold magenta]\u25b6[/] Batch video generation from topics, CSV, or RSS.")
app.add_typer(content_app, name="content", help="[bold bright_green]\u25b6[/] Content planning, calendars, trending topics, series.")
app.add_typer(effects_app, name="effects", help="[bold bright_cyan]\u25b6[/] Post-production: zoom, silence removal, B-roll, clips.")
app.add_typer(audio_app, name="audio", help="[bold yellow]\u25b6[/] Audio-first video generation from audio files.")
app.add_typer(agent_app, name="agent", help="[bold magenta]\u25b6[/] AI agent: Claude orchestrates end-to-end creation.")
app.add_typer(server_app, name="serve", help="[bold blue]\u25b6[/] Start the web server and dashboard.")

# Register top-level worker command
from aividio.cli.server import worker as _worker_cmd  # noqa: E402

app.command("worker", help="Start the background job worker.")(_worker_cmd)


@app.callback(invoke_without_command=True)
def _main_callback(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-V", help="Show version and exit."),
) -> None:
    """[bold bright_green]AIVidio[/] \u2014 AI-powered faceless video automation."""
    if version:
        from aividio.cli.theme import LOGO, TAGLINE, VERSION, console

        console.print(f"aividio [bold bright_green]{VERSION}[/bold bright_green]")
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        from aividio.cli.theme import LOGO, TAGLINE, VERSION, console

        console.print(LOGO)
        console.print(f"  {TAGLINE}   [dim]v{VERSION}[/dim]")
        console.print()
        console.print("  Run [bold bright_green]aividio --help[/bold bright_green] to see all commands.")
        console.print("  Run [bold bright_green]aividio generate video --topic \"...\"[/bold bright_green] to create a video.")
        console.print()


if __name__ == "__main__":
    app()
