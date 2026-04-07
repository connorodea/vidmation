"""Audio-first CLI commands — generate video from audio content."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from vidmation.cli.theme import console, error, success, styled_table, result_panel, spinner, header

audio_app = typer.Typer(no_args_is_help=True)


# ---------------------------------------------------------------------------
# vidmation audio generate
# ---------------------------------------------------------------------------

@audio_app.command("generate")
def audio_generate(
    file: str = typer.Option(
        ..., "--file", "-f", help="Path to the audio file (mp3, wav, m4a, etc.)."
    ),
    channel: str = typer.Option(
        "default", "--channel", "-c", help="Channel name."
    ),
    format: str = typer.Option(
        "landscape", "--format", help="Video format: landscape, portrait, short."
    ),
) -> None:
    """Generate a full video from an audio file.

    Takes an existing audio file (podcast episode, voiceover, lecture) and
    builds a video around it by transcribing, analyzing sections, generating
    visuals, and assembling the final output.

    Example:
        vidmation audio generate --file podcast.mp3 --channel default
        vidmation audio generate --file lecture.wav --format portrait
    """
    from vidmation.audio_first.pipeline import AudioFirstPipeline
    from vidmation.config.settings import get_settings
    from vidmation.db.engine import init_db
    from vidmation.utils.logging import setup_logging

    setup_logging()
    init_db()

    audio_path = Path(file)
    if not audio_path.exists():
        error(f"Audio file not found: {file}")
        raise typer.Exit(1)

    console.print(result_panel(
        "Audio-First Pipeline",
        [
            ("Audio file:", audio_path.name),
            ("Channel:", channel),
            ("Format:", format),
        ],
    ))

    pipeline = AudioFirstPipeline(settings=get_settings())

    with spinner("Running audio-first pipeline..."):
        try:
            work_dir = pipeline.generate(
                audio_path=audio_path,
                channel_name=channel,
                format=format,
            )
        except FileNotFoundError as exc:
            error(str(exc))
            raise typer.Exit(1)
        except ValueError as exc:
            error(str(exc))
            raise typer.Exit(1)

    # Load the pipeline state for display.
    state_path = work_dir / "pipeline_state.json"
    state: dict = {}
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))

    console.print()
    console.print(result_panel(
        "Pipeline Checkpoint",
        [
            ("Work directory:", str(work_dir)),
            ("Sections found:", str(state.get("sections_count", "N/A"))),
            ("Words transcribed:", str(state.get("words_count", "N/A"))),
            ("Status:", state.get("status", "unknown")),
            ("Steps completed:", ", ".join(state.get("steps_completed", []))),
            ("Steps remaining:", ", ".join(state.get("steps_remaining", []))),
        ],
    ))


# ---------------------------------------------------------------------------
# vidmation audio analyze
# ---------------------------------------------------------------------------

@audio_app.command("analyze")
def audio_analyze(
    file: str = typer.Option(
        ..., "--file", "-f", help="Path to the audio file."
    ),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Save analysis to JSON file."
    ),
) -> None:
    """Analyze an audio file without generating a video.

    Transcribes the audio, detects sections, and displays a summary.
    Useful for previewing what the audio-first pipeline will produce.

    Example:
        vidmation audio analyze --file podcast.mp3
        vidmation audio analyze --file lecture.wav --output analysis.json
    """
    from vidmation.audio_first.pipeline import AudioFirstPipeline
    from vidmation.config.settings import get_settings
    from vidmation.db.engine import init_db
    from vidmation.utils.logging import setup_logging

    setup_logging()
    init_db()

    audio_path = Path(file)
    if not audio_path.exists():
        error(f"Audio file not found: {file}")
        raise typer.Exit(1)

    pipeline = AudioFirstPipeline(settings=get_settings())

    with spinner("Analyzing audio..."):
        try:
            analysis = pipeline.analyze_audio(audio_path)
        except FileNotFoundError as exc:
            error(str(exc))
            raise typer.Exit(1)
        except ValueError as exc:
            error(str(exc))
            raise typer.Exit(1)

    # Display summary.
    console.print()
    console.print(result_panel(
        "Audio Analysis",
        [
            ("Audio file:", audio_path.name),
            ("Duration:", f"{analysis.get('total_duration_seconds', 0):.1f}s"),
            ("Words:", str(analysis.get("word_count", 0))),
            ("Topic:", analysis.get("overall_topic", "N/A")),
            ("Suggested title:", analysis.get("suggested_title", "N/A")),
        ],
    ))

    # Display sections table.
    sections = analysis.get("sections", [])
    if sections:
        table = styled_table(f"Detected Sections ({len(sections)})")
        table.add_column("#", style="dim", width=4)
        table.add_column("Heading", style="bold", max_width=40)
        table.add_column("Start", width=8, justify="right")
        table.add_column("End", width=8, justify="right")
        table.add_column("Tone", width=15)
        table.add_column("Summary", max_width=50)

        for section in sections:
            start = section.get("start_seconds", 0)
            end = section.get("end_seconds", 0)
            table.add_row(
                str(section.get("section_number", "")),
                section.get("heading", "N/A"),
                _format_time(start),
                _format_time(end),
                section.get("tone", ""),
                _truncate(section.get("summary", ""), 47),
            )

        console.print(table)

    # Display segments table.
    segments = analysis.get("segments", [])
    if segments:
        console.print()
        table = styled_table(f"Audio Segments ({len(segments)})")
        table.add_column("#", style="dim", width=4)
        table.add_column("Start", width=8, justify="right")
        table.add_column("End", width=8, justify="right")
        table.add_column("Duration", width=10, justify="right")
        table.add_column("Energy", width=8)

        for i, seg in enumerate(segments, 1):
            table.add_row(
                str(i),
                _format_time(seg.get("start", 0)),
                _format_time(seg.get("end", 0)),
                f"{seg.get('duration', 0):.1f}s",
                seg.get("energy", "medium"),
            )

        console.print(table)

    # Save to file if requested.
    if output:
        output_path = Path(output)
        # Convert for JSON serialization (remove raw word list for readability).
        save_data = {k: v for k, v in analysis.items() if k != "words"}
        save_data["word_count"] = analysis.get("word_count", len(analysis.get("words", [])))
        output_path.write_text(
            json.dumps(save_data, indent=2, default=str),
            encoding="utf-8",
        )
        success(f"Analysis saved to {output_path}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_time(seconds: float) -> str:
    """Format seconds as MM:SS."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis if needed."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
