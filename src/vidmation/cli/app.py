"""Main Typer application — entry point for the ``vidmation`` CLI."""

from __future__ import annotations

import typer

from vidmation.cli.audio import audio_app
from vidmation.cli.batch import batch_app
from vidmation.cli.channel import channel_app
from vidmation.cli.content import content_app
from vidmation.cli.generate import generate_app
from vidmation.cli.job import job_app
from vidmation.cli.server import server_app

app = typer.Typer(
    name="vidmation",
    help="AI-powered faceless YouTube video automation platform.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Register sub-command groups
app.add_typer(generate_app, name="generate", help="Generate videos, scripts, voiceovers, and thumbnails.")
app.add_typer(channel_app, name="channel", help="Manage YouTube channels.")
app.add_typer(job_app, name="job", help="View and manage pipeline jobs.")
app.add_typer(server_app, name="serve", help="Start the web server.")
app.add_typer(batch_app, name="batch", help="Batch video generation from topics, CSV, or RSS.")
app.add_typer(audio_app, name="audio", help="Audio-first video generation from audio files.")
app.add_typer(content_app, name="content", help="Content planning, calendars, trending topics, and series.")

# Register top-level worker/serve commands
from vidmation.cli.server import worker as _worker_cmd, serve as _serve_cmd  # noqa: E402

app.command("worker", help="Start the background job worker.")(_worker_cmd)


@app.callback()
def _main_callback() -> None:
    """VIDMATION — faceless YouTube video automation."""
    pass


if __name__ == "__main__":
    app()
