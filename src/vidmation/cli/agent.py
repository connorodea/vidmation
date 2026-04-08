"""CLI commands for the AI agent orchestrator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.panel import Panel

if TYPE_CHECKING:
    from vidmation.agent.orchestrator import AgentOrchestrator
    from vidmation.pipeline.context import PipelineContext

from vidmation.cli.theme import console, error, header, result_panel, spinner, styled_table, warning
from vidmation.config.profiles import ChannelProfile, get_default_profile, load_profile
from vidmation.config.settings import get_settings

agent_app = typer.Typer(
    help="AI-powered video creation agent.  Let Claude coordinate the entire pipeline.",
)


def _load_profile(channel: str) -> ChannelProfile:
    """Load a channel profile by name, falling back to default."""
    if channel == "default":
        return get_default_profile()

    settings = get_settings()
    profile_path = settings.profiles_dir / f"{channel}.yaml"
    if profile_path.exists():
        return load_profile(profile_path)

    # Try with .yml extension
    profile_path = settings.profiles_dir / f"{channel}.yml"
    if profile_path.exists():
        return load_profile(profile_path)

    warning(f"Profile '{channel}' not found. Using default profile.")
    return get_default_profile()


@agent_app.command("create")
def create_video(
    topic: str = typer.Argument(..., help="Video topic or prompt."),
    channel: str = typer.Option("default", "--channel", "-c", help="Channel profile name."),
    duration: str = typer.Option("10-12 minutes", "--duration", "-d", help="Target duration."),
    format: str = typer.Option("landscape", "--format", "-f", help="Video format: landscape, portrait, short."),
    upload: bool = typer.Option(False, "--upload", "-u", help="Upload to YouTube when done."),
    budget: float = typer.Option(None, "--budget", "-b", help="Maximum budget in USD."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed agent thinking."),
) -> None:
    """Let the AI agent create a complete video from a topic.

    The agent will analyse the topic, create a production plan, and execute
    each step -- generating script, voiceover, captions, media, assembly,
    effects, and export -- making intelligent decisions at every stage.
    """
    from vidmation.agent.orchestrator import AgentOrchestrator

    profile = _load_profile(channel)
    settings = get_settings()

    console.print(header("AI Agent", "Claude-powered end-to-end video creation"))
    console.print(result_panel(
        "Video Creation",
        [
            ("Topic:", topic),
            ("Channel:", f"{profile.name} ({profile.niche})"),
            ("Duration:", duration),
            ("Format:", format),
            ("Budget:", f"${budget:.2f}" if budget else "Unlimited"),
            ("Upload:", "Yes" if upload else "No"),
        ],
    ))

    # Step tracking for progress display
    steps_completed: list[str] = []

    def step_callback(step_name: str, detail: str) -> None:
        steps_completed.append(step_name)
        if verbose:
            console.print(f"  [dim]{step_name}:[/dim] {detail}")
        else:
            console.print(f"  [green]>[/green] {step_name}")

    try:
        agent = AgentOrchestrator(settings=settings)

        with spinner("Agent is working..."):
            ctx = agent.create_video(
                topic=topic,
                channel_profile=profile,
                target_duration=duration,
                format=format,
                upload=upload,
                budget_limit=budget,
                step_callback=step_callback,
            )

        # Show summary
        console.print()
        _show_summary(ctx, agent)

    except ValueError as exc:
        error(f"Configuration error: {exc}")
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        warning("Agent interrupted by user.")
        raise typer.Exit(code=130)
    except Exception as exc:
        error(f"Agent error: {exc}")
        if verbose:
            console.print_exception()
        raise typer.Exit(code=1)


@agent_app.command("plan")
def plan_video(
    topic: str = typer.Argument(..., help="Video topic to plan."),
    channel: str = typer.Option("default", "--channel", "-c", help="Channel profile name."),
) -> None:
    """Generate a production plan without executing it.

    The agent will analyse the topic and describe what steps it would take,
    which services it would use, and estimated costs -- without actually
    running anything.
    """
    from vidmation.agent.orchestrator import AgentOrchestrator

    profile = _load_profile(channel)
    settings = get_settings()

    console.print(header("Production Plan", "Plan Mode"))
    console.print(result_panel(
        "Plan Details",
        [
            ("Topic:", topic),
            ("Channel:", f"{profile.name} ({profile.niche})"),
        ],
    ))

    try:
        agent = AgentOrchestrator(settings=settings)

        with spinner("Agent is planning..."):
            plan = agent.plan_video(topic=topic, channel_profile=profile)

        console.print()
        console.print(Panel(plan, title="Production Plan", border_style="cyan"))

    except ValueError as exc:
        error(f"Configuration error: {exc}")
        raise typer.Exit(code=1)
    except Exception as exc:
        error(str(exc))
        raise typer.Exit(code=1)


@agent_app.command("review")
def review_video(
    video_id: str = typer.Argument(..., help="Video ID to review."),
) -> None:
    """AI reviews an existing video and suggests improvements.

    Loads the pipeline context for the given video ID and asks the agent
    to evaluate quality, monetisation compliance, and viewer retention.
    """
    from vidmation.agent.orchestrator import AgentOrchestrator
    from vidmation.pipeline.context import PipelineContext

    settings = get_settings()

    # Try to load context from output dir
    context_path = settings.output_dir / video_id / "pipeline_context.json"
    if not context_path.exists():
        error(f"Context not found: {context_path}")
        raise typer.Exit(code=1)

    try:
        context_data = json.loads(context_path.read_text(encoding="utf-8"))

        # Reconstruct a minimal context for review
        profile = get_default_profile()
        ctx = PipelineContext(
            video_id=video_id,
            channel_profile=profile,
            topic=context_data.get("topic", "Unknown"),
            format=context_data.get("format", "landscape"),
            work_dir=Path(context_data.get("work_dir", str(settings.output_dir / video_id))),
        )
        ctx.script = context_data.get("script")
        ctx.voiceover_duration = context_data.get("voiceover_duration")
        ctx.completed_stages = context_data.get("completed_stages", [])

        agent = AgentOrchestrator(settings=settings)

        with spinner("Agent is reviewing..."):
            review = agent.review_video(ctx)

        console.print()
        console.print(Panel(review, title="Video Review", border_style="cyan"))

    except json.JSONDecodeError:
        error(f"Invalid JSON in context file: {context_path}")
        raise typer.Exit(code=1)
    except Exception as exc:
        error(str(exc))
        raise typer.Exit(code=1)


def _show_summary(ctx: "PipelineContext", agent: "AgentOrchestrator") -> None:
    """Display a summary table after video creation."""
    table = styled_table("Video Creation Summary")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Video ID", ctx.video_id)
    table.add_row("Topic", ctx.topic)

    if ctx.script:
        table.add_row("Title", ctx.script.get("title", "N/A"))
        table.add_row("Sections", str(len(ctx.script.get("sections", []))))

    if ctx.voiceover_duration:
        table.add_row("Duration", f"{ctx.voiceover_duration:.1f}s ({ctx.voiceover_duration / 60:.1f} min)")

    if ctx.final_video_path:
        table.add_row("Video", str(ctx.final_video_path))

    if ctx.thumbnail_path:
        table.add_row("Thumbnail", str(ctx.thumbnail_path))

    table.add_row("Stages completed", str(len(ctx.completed_stages)))

    toolkit = getattr(agent, "_toolkit", None)
    if toolkit:
        table.add_row("Total cost", f"${toolkit.total_cost:.4f}")

    table.add_row("Work directory", str(ctx.work_dir))

    console.print(table)
