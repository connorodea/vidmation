"""Content planning CLI — generate calendars, discover trends, manage series."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel

from vidmation.cli.theme import console, success, info, styled_table, spinner
from vidmation.config.settings import get_settings
from vidmation.db.engine import init_db

content_app = typer.Typer(no_args_is_help=True)


# ---------------------------------------------------------------------------
# vidmation content plan
# ---------------------------------------------------------------------------

@content_app.command("plan")
def content_plan(
    channel: str = typer.Option("default", "--channel", "-c", help="Channel name."),
    weeks: int = typer.Option(4, "--weeks", "-w", help="Number of weeks to plan."),
    videos_per_week: int = typer.Option(3, "--vpw", help="Videos per week."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save calendar JSON to file."),
    save: bool = typer.Option(True, "--save/--no-save", help="Persist calendar to data dir."),
) -> None:
    """Generate an AI-powered content calendar.

    Creates a multi-week content plan with topics, formats, keywords,
    and priorities.  Saves to the data directory by default.
    """
    from vidmation.content.calendar import ContentCalendar
    from vidmation.content.planner import ContentPlanner

    init_db()
    settings = get_settings()

    with spinner("Generating content calendar..."):
        planner = ContentPlanner(settings=settings)
        entries = planner.generate_content_calendar(
            channel_name=channel,
            weeks=weeks,
            videos_per_week=videos_per_week,
        )

    # Display results
    table = styled_table(f"Content Calendar — {channel} ({weeks} weeks)")
    table.add_column("Date", style="cyan", width=12)
    table.add_column("Title", style="bold", max_width=40)
    table.add_column("Format", style="dim", width=12)
    table.add_column("Type", width=10)
    table.add_column("Priority", width=8)
    table.add_column("Keywords", style="dim", max_width=30)

    for entry in entries:
        priority = entry.get("priority", "")
        priority_style = {
            "high": "[red]high[/red]",
            "medium": "[yellow]medium[/yellow]",
            "low": "[dim]low[/dim]",
        }.get(priority, priority)

        keywords = ", ".join(entry.get("keywords", [])[:3])

        table.add_row(
            entry.get("date", ""),
            entry.get("title", entry.get("topic", "")),
            entry.get("format", ""),
            entry.get("content_type", ""),
            priority_style,
            keywords,
        )

    console.print(table)

    # Save to calendar file
    if save:
        cal = ContentCalendar()
        cal.channel_name = channel
        cal.add_entries(entries)
        path = cal.save()
        success(f"Calendar saved: {path}")
        info(f"Calendar ID: [cyan]{cal.calendar_id}[/cyan]")

    # Optional JSON export
    if output:
        Path(output).write_text(json.dumps(entries, indent=2), encoding="utf-8")
        success(f"JSON exported to {output}")

    console.print(f"\n[dim]Total entries: {len(entries)}[/dim]")


# ---------------------------------------------------------------------------
# vidmation content trending
# ---------------------------------------------------------------------------

@content_app.command("trending")
def content_trending(
    niche: str = typer.Option(..., "--niche", "-n", help="Content niche to analyse."),
    count: int = typer.Option(20, "--count", "-c", help="Number of topics to return."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save JSON to file."),
) -> None:
    """Discover trending topics in a niche.

    Uses AI to identify timely, high-potential video topics.
    """
    from vidmation.content.planner import ContentPlanner

    settings = get_settings()

    with spinner(f"Finding trending topics in '{niche}'..."):
        planner = ContentPlanner(settings=settings)
        topics = planner.trending_topics(niche=niche, count=count)

    table = styled_table(f"Trending Topics — {niche}")
    table.add_column("Topic", style="bold", max_width=40)
    table.add_column("Relevance", width=10)
    table.add_column("Competition", width=12)
    table.add_column("Timeliness", width=14)
    table.add_column("Suggested Title", style="dim", max_width=40)

    for t in topics:
        score = t.get("relevance_score", 0)
        if score >= 0.7:
            score_str = f"[green]{score:.0%}[/green]"
        elif score >= 0.4:
            score_str = f"[yellow]{score:.0%}[/yellow]"
        else:
            score_str = f"[dim]{score:.0%}[/dim]"

        competition = t.get("competition", "")
        comp_style = {
            "low": "[green]low[/green]",
            "medium": "[yellow]medium[/yellow]",
            "high": "[red]high[/red]",
        }.get(competition, competition)

        table.add_row(
            t.get("topic", ""),
            score_str,
            comp_style,
            t.get("timeliness", ""),
            t.get("suggested_title", ""),
        )

    console.print(table)

    if output:
        Path(output).write_text(json.dumps(topics, indent=2), encoding="utf-8")
        success(f"JSON saved to {output}")


# ---------------------------------------------------------------------------
# vidmation content series
# ---------------------------------------------------------------------------

@content_app.command("series")
def content_series(
    channel: str = typer.Option("default", "--channel", "-c", help="Filter by channel name."),
    suggest: bool = typer.Option(False, "--suggest", "-s", help="Use AI to suggest new series ideas."),
) -> None:
    """List and manage video series.

    Shows all existing series with episode counts and progress.
    Use --suggest to get AI-generated series ideas.
    """
    from vidmation.content.series import SeriesManager

    init_db()
    manager = SeriesManager()

    if suggest:
        from vidmation.content.planner import ContentPlanner

        settings = get_settings()

        with spinner("Generating series ideas..."):
            planner = ContentPlanner(settings=settings)
            ideas = planner.suggest_series(channel_name=channel)

        for idx, idea in enumerate(ideas, 1):
            panel_text = f"[bold]{idea.get('description', '')}[/bold]\n\n"
            panel_text += f"Episodes: {idea.get('episode_count', 'TBD')}\n\n"
            topics = idea.get("topics", [])
            for ep_idx, topic in enumerate(topics, 1):
                panel_text += f"  {ep_idx}. {topic}\n"

            console.print(Panel(
                panel_text,
                title=f"[cyan]{idx}. {idea.get('series_name', 'Untitled')}[/cyan]",
                border_style="dim",
            ))
        return

    # List existing series
    series_list = manager.list_series(channel_name=channel if channel != "default" else None)

    if not series_list:
        console.print("[dim]No series found.[/dim]")
        console.print("  Create one: [bold]vidmation content series --suggest --channel default[/bold]")
        return

    table = styled_table("Video Series")
    table.add_column("Name", style="bold")
    table.add_column("Channel", style="dim")
    table.add_column("Episodes", width=10)
    table.add_column("Completed", width=10)
    table.add_column("Progress", width=20)
    table.add_column("ID", style="dim", width=12)

    for s in series_list:
        total = s.get("episode_count", 0)
        done = s.get("completed_count", 0)
        pct = int(done / total * 100) if total else 0
        bar_filled = pct // 5
        bar = f"[green]{'#' * bar_filled}[/green][dim]{'.' * (20 - bar_filled)}[/dim] {pct}%"

        table.add_row(
            s.get("name", ""),
            s.get("channel_name", ""),
            str(total),
            str(done),
            bar,
            s.get("id", "")[:12],
        )

    console.print(table)


# ---------------------------------------------------------------------------
# vidmation content gaps
# ---------------------------------------------------------------------------

@content_app.command("gaps")
def content_gaps(
    channel: str = typer.Option("default", "--channel", "-c", help="Channel to analyse."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save JSON to file."),
) -> None:
    """Analyse content gaps for a channel.

    Examines existing videos and identifies untapped topics and
    growth opportunities.
    """
    from vidmation.content.planner import ContentPlanner

    init_db()
    settings = get_settings()

    with spinner(f"Analysing content gaps for '{channel}'..."):
        planner = ContentPlanner(settings=settings)
        result = planner.analyze_content_gaps(channel_name=channel)

    # Covered topics
    covered = result.get("covered_topics", [])
    if covered:
        console.print(Panel(
            "\n".join(f"  - {t}" for t in covered[:15]),
            title="[cyan]Covered Topics[/cyan]",
            border_style="dim",
        ))

    # Gaps
    gaps = result.get("gaps", [])
    if gaps:
        table = styled_table("Content Gaps")
        table.add_column("Topic", style="bold", max_width=40)
        table.add_column("Reason", style="dim", max_width=60)

        for gap in gaps:
            if isinstance(gap, dict):
                table.add_row(gap.get("topic", ""), gap.get("reason", ""))
            else:
                table.add_row(str(gap), "")

        console.print(table)

    # Recommendations
    recommendations = result.get("recommendations", [])
    if recommendations:
        console.print(Panel(
            "\n".join(f"  {i}. {r}" for i, r in enumerate(recommendations, 1)),
            title="[green]Recommendations[/green]",
            border_style="green",
        ))

    if output:
        Path(output).write_text(json.dumps(result, indent=2), encoding="utf-8")
        success(f"Full analysis saved to {output}")


# ---------------------------------------------------------------------------
# vidmation content keywords
# ---------------------------------------------------------------------------

@content_app.command("keywords")
def content_keywords(
    topic: str = typer.Option(..., "--topic", "-t", help="Topic to research."),
    niche: str = typer.Option("general", "--niche", "-n", help="Content niche."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save JSON to file."),
) -> None:
    """Research keywords for a video topic.

    Analyses keyword opportunity, competition, and suggests angles.
    """
    from vidmation.seo.optimizer import SEOOptimizer

    settings = get_settings()

    with spinner("Researching keywords..."):
        seo = SEOOptimizer(settings=settings)
        result = seo.keyword_research(topic=topic, niche=niche)

    # Primary keywords
    primary = result.get("primary_keywords", [])
    if primary:
        console.print(Panel(
            "  ".join(f"[bold cyan]{kw}[/bold cyan]" for kw in primary),
            title="Primary Keywords",
        ))

    # Secondary keywords
    secondary = result.get("secondary_keywords", [])
    if secondary:
        console.print(Panel(
            "  ".join(f"[yellow]{kw}[/yellow]" for kw in secondary),
            title="Secondary Keywords",
        ))

    # Long-tail
    longtail = result.get("long_tail", [])
    if longtail:
        console.print(Panel(
            "\n".join(f"  - {kw}" for kw in longtail),
            title="Long-Tail Keywords",
        ))

    # Competition
    competition = result.get("competition_estimate", "unknown")
    comp_style = {
        "low": "[green]LOW[/green]",
        "medium": "[yellow]MEDIUM[/yellow]",
        "high": "[red]HIGH[/red]",
    }.get(competition, competition)
    console.print(f"\nCompetition: {comp_style}")

    # Angles
    angles = result.get("suggested_angles", [])
    if angles:
        console.print(Panel(
            "\n".join(f"  {i}. {a}" for i, a in enumerate(angles, 1)),
            title="[green]Suggested Angles[/green]",
            border_style="green",
        ))

    if output:
        Path(output).write_text(json.dumps(result, indent=2), encoding="utf-8")
        success(f"Saved to {output}")
