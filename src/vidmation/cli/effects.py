"""CLI commands for post-production effects.

Provides sub-commands for magic zoom, silence removal, B-roll insertion,
emoji/SFX enhancement, and viral clip extraction.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from vidmation.cli.theme import (
    console,
    error,
    info,
    result_panel,
    spinner,
    styled_table,
    success,
    warning,
)

effects_app = typer.Typer(no_args_is_help=True)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _load_timestamps(timestamps_file: str | None, video_path: Path) -> list[dict]:
    """Load word timestamps from a JSON file or auto-transcribe the video.

    If *timestamps_file* is provided, loads from that file.  Otherwise,
    extracts audio from the video and runs Whisper transcription.

    Returns:
        List of ``{"word": str, "start": float, "end": float}`` dicts.
    """
    if timestamps_file:
        ts_path = Path(timestamps_file)
        if not ts_path.exists():
            error(f"Timestamps file not found: {ts_path}")
            raise typer.Exit(1)
        data = json.loads(ts_path.read_text(encoding="utf-8"))
        # Support both a flat list and a {"words": [...]} wrapper.
        if isinstance(data, list):
            return data
        return data.get("words", data.get("word_timestamps", []))

    # Auto-transcribe.
    from vidmation.config.settings import get_settings
    from vidmation.services.captions.whisper import WhisperCaptionGenerator
    from vidmation.utils.ffmpeg import run_ffmpeg

    info("No timestamps file provided; auto-transcribing...")

    # Extract audio.
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        audio_path = Path(tmp.name)

    run_ffmpeg(
        ["ffmpeg", "-y", "-i", str(video_path), "-vn", "-acodec", "pcm_s16le",
         "-ar", "16000", "-ac", "1", str(audio_path)],
        desc="Extract audio for transcription",
    )

    settings = get_settings()
    try:
        whisper = WhisperCaptionGenerator(settings=settings, backend="local")
    except (ImportError, ValueError):
        try:
            whisper = WhisperCaptionGenerator(settings=settings, backend="replicate")
        except ValueError:
            error(
                "No Whisper backend available.  "
                "Provide a timestamps JSON file with --timestamps."
            )
            audio_path.unlink(missing_ok=True)
            raise typer.Exit(1)

    with spinner("Transcribing audio..."):
        word_timestamps = whisper.transcribe(audio_path)

    audio_path.unlink(missing_ok=True)

    success(f"Transcribed {len(word_timestamps)} words")
    return word_timestamps


def _validate_input(video_path: str) -> Path:
    """Validate and return the input video path."""
    path = Path(video_path)
    if not path.exists():
        error(f"Video file not found: {video_path}")
        raise typer.Exit(1)
    return path


# ---------------------------------------------------------------------------
# vidmation effects zoom
# ---------------------------------------------------------------------------

@effects_app.command("zoom")
def effects_zoom(
    input: str = typer.Option(..., "--input", "-i", help="Input video file."),
    style: str = typer.Option(
        "smooth", "--style", "-s",
        help="Zoom style: smooth, crash, expo, linear.",
    ),
    max_zooms: int = typer.Option(10, "--max-zooms", "-n", help="Maximum zoom effects."),
    timestamps: Optional[str] = typer.Option(
        None, "--timestamps", "-t",
        help="Word timestamps JSON file (auto-transcribes if not provided).",
    ),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path."),
) -> None:
    """Apply magic zoom effects at emphasis points in a video.

    Detects key moments (statistics, transitions, emotional peaks) and
    applies smooth zoom-in/out effects.

    Examples:
        vidmation effects zoom --input video.mp4 --style smooth
        vidmation effects zoom -i video.mp4 -s crash -n 5 -o output.mp4
    """
    from vidmation.effects.magic_zoom import MagicZoom
    from vidmation.utils.logging import setup_logging

    setup_logging()

    video_path = _validate_input(input)
    word_timestamps = _load_timestamps(timestamps, video_path)

    output_path = Path(output) if output else None

    console.print(result_panel(
        "Magic Zoom",
        [
            ("Input:", video_path.name),
            ("Style:", style),
            ("Max zooms:", str(max_zooms)),
            ("Words:", str(len(word_timestamps))),
        ],
    ))

    zoom = MagicZoom()

    with spinner("Detecting emphasis points..."):
        zoom_points = zoom.detect_emphasis_points(
            word_timestamps=word_timestamps,
            max_zooms=max_zooms,
        )

    if zoom_points:
        table = styled_table(f"Detected {len(zoom_points)} Zoom Points")
        table.add_column("Time", width=10, justify="right")
        table.add_column("Style", width=10)
        table.add_column("Intensity", width=10, justify="right")
        table.add_column("Reason", max_width=40)

        for zp in zoom_points:
            table.add_row(
                f"{zp['start']:.1f}s",
                zp.get("style", style),
                f"{zp['intensity']:.0%}",
                zp.get("reason", ""),
            )
        console.print(table)

    with spinner("Applying zoom effects..."):
        result = zoom.auto_zoom(
            video_path=video_path,
            word_timestamps=word_timestamps,
            style=style,
            max_zooms=max_zooms,
            output_path=output_path,
        )

    success(f"Zoom effects applied! Output: {result}")


# ---------------------------------------------------------------------------
# vidmation effects silence
# ---------------------------------------------------------------------------

@effects_app.command("silence")
def effects_silence(
    input: str = typer.Option(..., "--input", "-i", help="Input video file."),
    mode: str = typer.Option(
        "normal", "--mode", "-m",
        help="Removal mode: normal, fast, extra_fast.",
    ),
    fillers: bool = typer.Option(True, "--fillers/--no-fillers", help="Also remove filler words."),
    timestamps: Optional[str] = typer.Option(
        None, "--timestamps", "-t",
        help="Word timestamps JSON file (needed for filler removal).",
    ),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path."),
) -> None:
    """Remove silence and filler words from a video.

    Detects silent segments and optionally removes filler words like
    "um", "uh", "like", "you know", etc.

    Examples:
        vidmation effects silence --input video.mp4 --mode fast
        vidmation effects silence -i video.mp4 -m extra_fast --no-fillers
    """
    from vidmation.effects.silence_remover import SilenceRemover
    from vidmation.utils.logging import setup_logging

    setup_logging()

    video_path = _validate_input(input)
    output_path = Path(output) if output else None

    console.print(result_panel(
        "Silence Remover",
        [
            ("Input:", video_path.name),
            ("Mode:", mode),
            ("Remove fillers:", str(fillers)),
        ],
    ))

    remover = SilenceRemover()

    if fillers:
        word_timestamps = _load_timestamps(timestamps, video_path)

        with spinner("Smart trimming (silence + fillers)..."):
            result_path, stats = remover.smart_trim(
                video_path=video_path,
                word_timestamps=word_timestamps,
                mode=mode,
                remove_fillers=True,
                output_path=output_path,
            )

        console.print(result_panel(
            "Results",
            [
                ("Original duration:", f"{stats['original_duration']:.1f}s"),
                ("New duration:", f"{stats['new_duration']:.1f}s"),
                ("Removed:", f"{stats['removed_seconds']:.1f}s"),
                ("Segments cut:", str(stats["segments_cut"])),
                ("Fillers removed:", str(stats["fillers_removed"])),
                ("Output:", str(result_path)),
            ],
        ))
    else:
        with spinner("Removing silence..."):
            result_path = remover.remove_silence(
                video_path=video_path,
                mode=mode,
                output_path=output_path,
            )

        success(f"Silence removed! Output: {result_path}")


# ---------------------------------------------------------------------------
# vidmation effects broll
# ---------------------------------------------------------------------------

@effects_app.command("broll")
def effects_broll(
    input: str = typer.Option(..., "--input", "-i", help="Input video file."),
    max_clips: int = typer.Option(8, "--max-clips", "-n", help="Maximum B-roll clips."),
    blend: str = typer.Option(
        "crossfade", "--blend", "-b",
        help="Blend mode: crossfade, cut, picture_in_picture.",
    ),
    timestamps: Optional[str] = typer.Option(
        None, "--timestamps", "-t",
        help="Word timestamps JSON file (auto-transcribes if not provided).",
    ),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path."),
) -> None:
    """Auto-insert contextual B-roll footage into a video.

    Analyzes the transcript to find moments that benefit from B-roll,
    searches stock media for matching clips, and inserts them.

    Examples:
        vidmation effects broll --input video.mp4 --max-clips 8
        vidmation effects broll -i video.mp4 -b picture_in_picture -n 5
    """
    from vidmation.effects.magic_broll import MagicBRoll
    from vidmation.utils.logging import setup_logging

    setup_logging()

    video_path = _validate_input(input)
    word_timestamps = _load_timestamps(timestamps, video_path)
    output_path = Path(output) if output else None

    console.print(result_panel(
        "Magic B-Roll",
        [
            ("Input:", video_path.name),
            ("Max clips:", str(max_clips)),
            ("Blend mode:", blend),
            ("Words:", str(len(word_timestamps))),
        ],
    ))

    broll = MagicBRoll()

    with spinner("Analyzing transcript for B-roll opportunities..."):
        suggestions = broll.analyze_transcript(
            word_timestamps=word_timestamps,
            max_clips=max_clips,
        )

    if suggestions:
        table = styled_table(f"B-Roll Suggestions ({len(suggestions)})")
        table.add_column("Time", width=12, justify="right")
        table.add_column("Priority", width=8, justify="center")
        table.add_column("Visual Query", max_width=30)
        table.add_column("Reason", max_width=30)

        for s in suggestions:
            table.add_row(
                f"{s['start']:.1f}-{s['end']:.1f}s",
                str(s["priority"]),
                s["visual_query"],
                s.get("reason", ""),
            )
        console.print(table)

    with spinner("Sourcing and inserting B-roll..."):
        result = broll.auto_broll(
            video_path=video_path,
            word_timestamps=word_timestamps,
            max_clips=max_clips,
            blend_mode=blend,
            output_path=output_path,
        )

    success(f"B-roll inserted! Output: {result}")


# ---------------------------------------------------------------------------
# vidmation effects emoji
# ---------------------------------------------------------------------------

@effects_app.command("emoji")
def effects_emoji(
    input: str = typer.Option(..., "--input", "-i", help="Input video file."),
    emojis: bool = typer.Option(True, "--emojis/--no-emojis", help="Add emoji overlays."),
    sfx: bool = typer.Option(True, "--sfx/--no-sfx", help="Add sound effects."),
    timestamps: Optional[str] = typer.Option(
        None, "--timestamps", "-t",
        help="Word timestamps JSON file (auto-transcribes if not provided).",
    ),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path."),
) -> None:
    """Auto-add emojis and sound effects to a video.

    Detects keywords in the transcript and overlays matching emojis.
    Optionally adds sound effects at transition and emphasis points.

    Examples:
        vidmation effects emoji --input video.mp4
        vidmation effects emoji -i video.mp4 --no-sfx
    """
    from vidmation.effects.emoji_sfx import EmojiSFXEngine
    from vidmation.utils.logging import setup_logging

    setup_logging()

    video_path = _validate_input(input)
    word_timestamps = _load_timestamps(timestamps, video_path)
    output_path = Path(output) if output else None

    console.print(result_panel(
        "Emoji & SFX Engine",
        [
            ("Input:", video_path.name),
            ("Emojis:", str(emojis)),
            ("SFX:", str(sfx)),
            ("Words:", str(len(word_timestamps))),
        ],
    ))

    engine = EmojiSFXEngine()

    with spinner("Enhancing video with emojis and SFX..."):
        result = engine.auto_enhance(
            video_path=video_path,
            word_timestamps=word_timestamps,
            emojis=emojis,
            sfx=sfx,
            output_path=output_path,
        )

    success(f"Enhancement complete! Output: {result}")


# ---------------------------------------------------------------------------
# vidmation effects clips
# ---------------------------------------------------------------------------

@effects_app.command("clips")
def effects_clips(
    input: str = typer.Option(..., "--input", "-i", help="Input video file."),
    count: int = typer.Option(5, "--count", "-n", help="Number of clips to extract."),
    format: str = typer.Option(
        "portrait", "--format", "-f",
        help="Clip format: portrait, square, landscape.",
    ),
    captions: bool = typer.Option(True, "--captions/--no-captions", help="Burn in captions."),
    min_duration: int = typer.Option(15, "--min-duration", help="Minimum clip duration (seconds)."),
    max_duration: int = typer.Option(60, "--max-duration", help="Maximum clip duration (seconds)."),
    timestamps: Optional[str] = typer.Option(
        None, "--timestamps", "-t",
        help="Word timestamps JSON file (auto-transcribes if not provided).",
    ),
    output_dir: Optional[str] = typer.Option(
        None, "--output-dir", "-o", help="Output directory for clips.",
    ),
) -> None:
    """Extract viral short-form clips from a long-form video.

    Analyzes the transcript for clip-worthy segments, extracts them,
    reformats to the target aspect ratio, and optionally burns in captions.

    Examples:
        vidmation effects clips --input video.mp4 --count 5 --format portrait
        vidmation effects clips -i podcast.mp4 -n 3 -f square --no-captions
    """
    from vidmation.effects.magic_clips import MagicClips
    from vidmation.utils.logging import setup_logging

    setup_logging()

    video_path = _validate_input(input)
    word_timestamps = _load_timestamps(timestamps, video_path)
    out_dir = Path(output_dir) if output_dir else None

    console.print(result_panel(
        "Magic Clips",
        [
            ("Input:", video_path.name),
            ("Count:", str(count)),
            ("Format:", format),
            ("Captions:", str(captions)),
            ("Duration:", f"{min_duration}-{max_duration}s"),
            ("Words:", str(len(word_timestamps))),
        ],
    ))

    clips_engine = MagicClips()

    # Show clip analysis first.
    with spinner("Analyzing video for viral moments..."):
        clip_candidates = clips_engine.analyze_for_clips(
            word_timestamps=word_timestamps,
            target_duration=(min_duration, max_duration),
            count=count,
        )

    if clip_candidates:
        table = styled_table(f"Clip Candidates ({len(clip_candidates)})")
        table.add_column("#", width=4, style="dim")
        table.add_column("Time", width=14, justify="right")
        table.add_column("Score", width=6, justify="right")
        table.add_column("Title", max_width=35)
        table.add_column("Reason", max_width=30)

        for i, clip in enumerate(clip_candidates, 1):
            dur = clip["end"] - clip["start"]
            table.add_row(
                str(i),
                f"{clip['start']:.1f}-{clip['end']:.1f}s ({dur:.0f}s)",
                str(clip["score"]),
                clip["title"],
                clip.get("reason", ""),
            )
        console.print(table)

    with spinner("Extracting and processing clips..."):
        output_paths = clips_engine.generate_clips(
            video_path=video_path,
            word_timestamps=word_timestamps,
            count=count,
            format=format,
            apply_captions=captions,
            target_duration=(min_duration, max_duration),
            output_dir=out_dir,
        )

    if output_paths:
        success(f"Generated {len(output_paths)} clips:")
        for p in output_paths:
            info(str(p))
    else:
        warning("No clips generated.")


# ---------------------------------------------------------------------------
# vidmation effects all
# ---------------------------------------------------------------------------

@effects_app.command("all")
def effects_all(
    input: str = typer.Option(..., "--input", "-i", help="Input video file."),
    timestamps: Optional[str] = typer.Option(
        None, "--timestamps", "-t",
        help="Word timestamps JSON file (auto-transcribes if not provided).",
    ),
    silence_mode: str = typer.Option("normal", "--silence-mode", help="Silence removal mode."),
    zoom_style: str = typer.Option("smooth", "--zoom-style", help="Zoom effect style."),
    max_zooms: int = typer.Option(10, "--max-zooms", help="Maximum zoom effects."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Final output file path."),
) -> None:
    """Apply all effects to a video in sequence.

    Runs the full effects pipeline:
    1. Silence + filler removal
    2. Magic zoom
    3. Emoji + SFX enhancement

    Examples:
        vidmation effects all --input video.mp4
        vidmation effects all -i video.mp4 --silence-mode fast --zoom-style crash
    """
    import tempfile

    from vidmation.effects.emoji_sfx import EmojiSFXEngine
    from vidmation.effects.magic_zoom import MagicZoom
    from vidmation.effects.silence_remover import SilenceRemover
    from vidmation.utils.logging import setup_logging

    setup_logging()

    video_path = _validate_input(input)
    word_timestamps = _load_timestamps(timestamps, video_path)

    if output:
        final_output = Path(output)
    else:
        final_output = video_path.parent / f"{video_path.stem}_enhanced{video_path.suffix}"

    console.print(result_panel(
        "Full Effects Pipeline",
        [
            ("Input:", video_path.name),
            ("Silence mode:", silence_mode),
            ("Zoom style:", zoom_style),
            ("Max zooms:", str(max_zooms)),
            ("Words:", str(len(word_timestamps))),
        ],
    ))

    with tempfile.TemporaryDirectory(prefix="vidmation_effects_") as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Step 1: Silence removal.
        info("[bold]Step 1/3:[/bold] Removing silence and fillers...")
        remover = SilenceRemover()
        trimmed_path = tmp_path / "step1_trimmed.mp4"

        with spinner("Trimming..."):
            trimmed_path, trim_stats = remover.smart_trim(
                video_path=video_path,
                word_timestamps=word_timestamps,
                mode=silence_mode,
                remove_fillers=True,
                output_path=trimmed_path,
            )

        console.print(
            f"  Removed [yellow]{trim_stats['removed_seconds']:.1f}s[/yellow] "
            f"({trim_stats['segments_cut']} cuts, {trim_stats['fillers_removed']} fillers)"
        )

        # Step 2: Magic zoom.
        info("[bold]Step 2/3:[/bold] Applying zoom effects...")
        zoomer = MagicZoom()
        zoomed_path = tmp_path / "step2_zoomed.mp4"

        with spinner("Zooming..."):
            zoomed_path = zoomer.auto_zoom(
                video_path=trimmed_path,
                word_timestamps=word_timestamps,
                style=zoom_style,
                max_zooms=max_zooms,
                output_path=zoomed_path,
            )

        console.print("  Zoom effects applied")

        # Step 3: Emoji + SFX.
        info("[bold]Step 3/3:[/bold] Adding emojis and sound effects...")
        enhancer = EmojiSFXEngine()

        with spinner("Enhancing..."):
            enhancer.auto_enhance(
                video_path=zoomed_path,
                word_timestamps=word_timestamps,
                emojis=True,
                sfx=True,
                output_path=final_output,
            )

        console.print("  Emojis and SFX added")

    console.print(result_panel(
        "Done",
        [
            ("Status:", "Full effects pipeline complete!"),
            ("Output:", str(final_output)),
        ],
    ))
