"""Batch CLI commands — generate multiple videos at once."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from vidmation.cli.theme import console, error, success, info, styled_table, spinner, warning

batch_app = typer.Typer(no_args_is_help=True)


# ---------------------------------------------------------------------------
# vidmation batch topics
# ---------------------------------------------------------------------------

@batch_app.command("topics")
def batch_topics(
    topics: list[str] = typer.Argument(
        ...,
        help='Video topics to generate (e.g., "topic1" "topic2" "topic3").',
    ),
    channel: str = typer.Option(
        "default", "--channel", "-c", help="Channel name."
    ),
    format: str = typer.Option(
        "landscape", "--format", "-f", help="Video format: landscape, portrait, short."
    ),
) -> None:
    """Queue multiple videos from a list of topics.

    Example:
        vidmation batch topics "10 facts about space" "History of pizza" --channel science
    """
    from vidmation.batch.generator import BatchVideoGenerator
    from vidmation.config.settings import get_settings
    from vidmation.db.engine import init_db
    from vidmation.utils.logging import setup_logging

    setup_logging()
    init_db()

    if not topics:
        error("At least one topic is required.")
        raise typer.Exit(1)

    generator = BatchVideoGenerator(settings=get_settings())

    with spinner(f"Queueing {len(topics)} videos..."):
        try:
            results = generator.from_topics(
                topics=topics,
                channel_name=channel,
                format=format,
            )
        except ValueError as exc:
            error(str(exc))
            raise typer.Exit(1)

    _display_batch_results(results, title="Batch Topics")


# ---------------------------------------------------------------------------
# vidmation batch csv
# ---------------------------------------------------------------------------

@batch_app.command("csv")
def batch_csv(
    csv_path: str = typer.Argument(
        ..., help="Path to CSV file with video topics."
    ),
    channel: str = typer.Option(
        "default", "--channel", "-c", help="Channel name."
    ),
) -> None:
    """Queue videos from a CSV file.

    The CSV must have a 'topic' column. Optional columns:
    title, format, tags, schedule_date, priority, notes.

    Example:
        vidmation batch csv data/topics.csv --channel default
    """
    from vidmation.batch.generator import BatchVideoGenerator
    from vidmation.config.settings import get_settings
    from vidmation.db.engine import init_db
    from vidmation.utils.logging import setup_logging

    setup_logging()
    init_db()

    csv_file = Path(csv_path)
    if not csv_file.exists():
        error(f"CSV file not found: {csv_path}")
        raise typer.Exit(1)

    generator = BatchVideoGenerator(settings=get_settings())

    with spinner(f"Processing CSV: {csv_file.name}..."):
        try:
            results = generator.from_csv(
                csv_path=csv_file,
                channel_name=channel,
            )
        except (ValueError, FileNotFoundError) as exc:
            error(str(exc))
            raise typer.Exit(1)

    _display_batch_results(results, title=f"Batch CSV ({csv_file.name})")


# ---------------------------------------------------------------------------
# vidmation batch ideas
# ---------------------------------------------------------------------------

@batch_app.command("ideas")
def batch_ideas(
    channel: str = typer.Option(
        "default", "--channel", "-c", help="Channel name."
    ),
    count: int = typer.Option(
        20, "--count", "-n", help="Number of topic ideas to generate."
    ),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output JSON file path."
    ),
    enqueue: bool = typer.Option(
        False,
        "--enqueue",
        help="Immediately queue the generated ideas as videos.",
    ),
) -> None:
    """Use AI to generate topic ideas based on the channel profile.

    By default, displays the ideas. Use --enqueue to immediately queue them.

    Example:
        vidmation batch ideas --channel science --count 10
        vidmation batch ideas --channel science --count 5 --enqueue
    """
    from vidmation.batch.generator import BatchVideoGenerator
    from vidmation.config.settings import get_settings
    from vidmation.db.engine import init_db
    from vidmation.utils.logging import setup_logging

    setup_logging()
    init_db()

    generator = BatchVideoGenerator(settings=get_settings())

    with spinner(f"Generating {count} topic ideas..."):
        try:
            ideas = generator.generate_topic_ideas(
                channel_name=channel,
                count=count,
            )
        except ValueError as exc:
            error(str(exc))
            raise typer.Exit(1)

    # Display ideas in a table.
    table = styled_table(f"Generated Topic Ideas ({len(ideas)})")
    table.add_column("#", style="dim", width=4)
    table.add_column("Topic", style="bold")
    table.add_column("Angle", style="italic")
    table.add_column("Type", width=12)
    table.add_column("Interest", width=10, justify="right")

    for i, idea in enumerate(ideas, 1):
        interest = idea.get("estimated_interest", 0.0)
        interest_str = f"{interest:.0%}" if isinstance(interest, (int, float)) else str(interest)
        table.add_row(
            str(i),
            idea.get("topic", "N/A"),
            idea.get("angle", ""),
            idea.get("content_type", ""),
            interest_str,
        )

    console.print(table)

    # Save to file if requested.
    if output:
        output_path = Path(output)
        output_path.write_text(json.dumps(ideas, indent=2), encoding="utf-8")
        success(f"Ideas saved to {output_path}")

    # Enqueue if requested.
    if enqueue:
        topics = [idea.get("topic", "") for idea in ideas if idea.get("topic")]
        if topics:
            info(f"Queueing {len(topics)} videos...")
            try:
                results = generator.from_topics(
                    topics=topics,
                    channel_name=channel,
                )
                _display_batch_results(results, title="Auto-Queued from Ideas")
            except ValueError as exc:
                error(f"Error queueing: {exc}")
                raise typer.Exit(1)


# ---------------------------------------------------------------------------
# vidmation batch rss
# ---------------------------------------------------------------------------

@batch_app.command("rss")
def batch_rss(
    feed_url: str = typer.Argument(
        ..., help="RSS/Atom feed URL to import topics from."
    ),
    channel: str = typer.Option(
        "default", "--channel", "-c", help="Channel name."
    ),
    max_items: int = typer.Option(
        10, "--max", "-m", help="Maximum number of feed items to process."
    ),
) -> None:
    """Generate videos from an RSS/blog feed.

    Fetches the feed, extracts titles and summaries, and queues each
    as a video topic. Great for repurposing blog content.

    Example:
        vidmation batch rss "https://blog.example.com/feed" --channel default --max 5
    """
    from vidmation.batch.generator import BatchVideoGenerator
    from vidmation.config.settings import get_settings
    from vidmation.db.engine import init_db
    from vidmation.utils.logging import setup_logging

    setup_logging()
    init_db()

    generator = BatchVideoGenerator(settings=get_settings())

    with spinner(f"Fetching RSS feed (max {max_items} items)..."):
        try:
            results = generator.from_rss(
                feed_url=feed_url,
                channel_name=channel,
                max_items=max_items,
            )
        except (ValueError, ImportError) as exc:
            error(str(exc))
            raise typer.Exit(1)

    _display_batch_results(results, title="Batch RSS Import")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _display_batch_results(
    results: list[tuple],
    title: str,
) -> None:
    """Display batch results in a Rich table."""
    if not results:
        warning("No videos were queued.")
        return

    table = styled_table(title)
    table.add_column("#", style="dim", width=4)
    table.add_column("Video ID", style="cyan", width=12)
    table.add_column("Job ID", style="cyan", width=12)
    table.add_column("Topic", max_width=60)

    for i, (video, job) in enumerate(results, 1):
        topic = getattr(video, "topic_prompt", "N/A")
        if len(topic) > 57:
            topic = topic[:57] + "..."
        table.add_row(
            str(i),
            str(video.id)[:8] + "...",
            str(job.id)[:8] + "...",
            topic,
        )

    console.print(table)
    success(f"{len(results)} video(s) queued successfully!")
    info("Track progress with: [bold]vidmation job list[/bold]")
