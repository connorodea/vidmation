"""Pipeline stage functions — each transforms the PipelineContext in place.

Every public ``stage_*`` function follows the same contract:
    (ctx: PipelineContext, settings: Settings) -> None
It reads what it needs from *ctx*, calls the appropriate service, and writes
its results back onto *ctx*.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vidmation.config.settings import Settings
    from vidmation.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Script generation
# ---------------------------------------------------------------------------

def stage_script_generation(ctx: PipelineContext, settings: Settings) -> None:
    """Generate a structured video script from the topic and channel profile."""
    from vidmation.services.scriptgen import create_script_generator

    logger.info("[script] Generating script for topic=%r", ctx.topic)

    generator = create_script_generator(settings=settings)
    script = generator.generate(topic=ctx.topic, profile=ctx.channel_profile)

    ctx.script = script

    # Persist script JSON to work directory
    script_path = ctx.work_dir / "script.json"
    script_path.write_text(json.dumps(script, indent=2), encoding="utf-8")

    logger.info(
        "[script] Done — %r (%d sections, ~%ds)",
        script.get("title", "untitled"),
        len(script.get("sections", [])),
        script.get("total_estimated_duration_seconds", 0),
    )


# ---------------------------------------------------------------------------
# 2. Text-to-speech
# ---------------------------------------------------------------------------

def stage_tts(ctx: PipelineContext, settings: Settings) -> None:
    """Generate voiceover audio from the script narration."""
    from vidmation.services.tts import create_tts_provider

    if ctx.script is None:
        raise RuntimeError("stage_tts requires ctx.script to be populated")

    logger.info("[tts] Synthesising voiceover")

    tts = create_tts_provider(settings=settings)

    # Build the full narration text from hook + sections + outro
    parts: list[str] = []
    if ctx.script.get("hook"):
        parts.append(ctx.script["hook"])
    for section in ctx.script.get("sections", []):
        parts.append(section["narration"])
    if ctx.script.get("outro"):
        parts.append(ctx.script["outro"])

    full_narration = "\n\n".join(parts)
    output_path = ctx.work_dir / "voiceover.mp3"

    result = tts.synthesize(
        text=full_narration,
        output_path=output_path,
        voice_config=ctx.channel_profile.voice,
    )

    ctx.voiceover_path = Path(result["path"])
    ctx.voiceover_duration = result.get("duration")

    logger.info(
        "[tts] Voiceover saved to %s (%.1fs)",
        ctx.voiceover_path,
        ctx.voiceover_duration or 0,
    )


# ---------------------------------------------------------------------------
# 3. Captions (Whisper transcription for word-level timestamps)
# ---------------------------------------------------------------------------

def stage_captions(ctx: PipelineContext, settings: Settings) -> None:
    """Run Whisper on the voiceover to generate word-level timestamps."""
    from vidmation.services.captions.whisper import WhisperCaptionGenerator

    if ctx.voiceover_path is None:
        raise RuntimeError("stage_captions requires ctx.voiceover_path")

    logger.info("[captions] Transcribing voiceover with Whisper")

    captioner = WhisperCaptionGenerator(settings=settings)
    result = captioner.transcribe(audio_path=ctx.voiceover_path)

    ctx.word_timestamps = result.get("word_timestamps", result.get("segments", []))

    # Persist timestamps
    ts_path = ctx.work_dir / "word_timestamps.json"
    ts_path.write_text(json.dumps(ctx.word_timestamps, indent=2), encoding="utf-8")

    logger.info(
        "[captions] Generated %d timestamp entries",
        len(ctx.word_timestamps),
    )


# ---------------------------------------------------------------------------
# 4. Media sourcing (stock video/images per script section)
# ---------------------------------------------------------------------------

def stage_media_sourcing(ctx: PipelineContext, settings: Settings) -> None:
    """Download stock media or generate AI images for each script section."""
    from vidmation.services.media import create_media_provider

    if ctx.script is None:
        raise RuntimeError("stage_media_sourcing requires ctx.script")

    logger.info("[media] Sourcing media for %d sections", len(ctx.script.get("sections", [])))

    media_provider = create_media_provider(settings=settings)
    clips: list[dict] = []

    for section in ctx.script.get("sections", []):
        idx = section["section_number"]
        query = section["visual_query"]
        visual_type = section["visual_type"]

        logger.info("[media] Section %d: query=%r type=%s", idx, query, visual_type)

        result = media_provider.search_and_download(
            query=query,
            media_type=visual_type,
            output_dir=ctx.work_dir / "media",
            section_index=idx,
        )

        clips.append({
            "path": str(result["path"]),
            "section_index": idx,
            "type": visual_type,
            "source": result.get("source", "unknown"),
            "attribution": result.get("attribution", ""),
        })

    ctx.media_clips = clips

    logger.info("[media] Sourced %d media clips", len(clips))


# ---------------------------------------------------------------------------
# 5. Video assembly (FFmpeg composition)
# ---------------------------------------------------------------------------

def stage_video_assembly(ctx: PipelineContext, settings: Settings) -> None:
    """Assemble voiceover, media clips, captions, and music into the final video."""
    from vidmation.utils.files import get_output_path

    if ctx.voiceover_path is None:
        raise RuntimeError("stage_video_assembly requires ctx.voiceover_path")
    if ctx.media_clips is None:
        raise RuntimeError("stage_video_assembly requires ctx.media_clips")

    logger.info("[assembly] Assembling final video")

    # Lazy import keeps heavy FFmpeg tooling out of module-load time
    from vidmation.services.compositor import compose_video  # type: ignore[import-not-found]

    output_path = get_output_path(ctx.video_id, "final.mp4")

    compose_result = compose_video(
        voiceover_path=ctx.voiceover_path,
        media_clips=ctx.media_clips,
        word_timestamps=ctx.word_timestamps,
        music_path=ctx.music_path,
        video_config=ctx.channel_profile.video,
        format=ctx.format,
        output_path=output_path,
    )

    ctx.final_video_path = Path(compose_result["path"])

    logger.info("[assembly] Final video saved to %s", ctx.final_video_path)


# ---------------------------------------------------------------------------
# 6. Thumbnail generation
# ---------------------------------------------------------------------------

def stage_thumbnail(ctx: PipelineContext, settings: Settings) -> None:
    """Generate a thumbnail image for the video."""
    from vidmation.services.imagegen import create_image_generator

    if ctx.script is None:
        raise RuntimeError("stage_thumbnail requires ctx.script")

    logger.info("[thumbnail] Generating thumbnail")

    generator = create_image_generator(settings=settings)

    title = ctx.script.get("title", ctx.topic)
    thumbnail_config = ctx.channel_profile.thumbnail

    result = generator.generate(
        prompt=f"YouTube thumbnail for: {title}. Style: {thumbnail_config.style}",
        output_path=ctx.work_dir / "thumbnail.png",
    )

    ctx.thumbnail_path = Path(result["path"])

    logger.info("[thumbnail] Saved to %s", ctx.thumbnail_path)


# ---------------------------------------------------------------------------
# 7. YouTube upload
# ---------------------------------------------------------------------------

def stage_upload(ctx: PipelineContext, settings: Settings) -> None:
    """Upload the finished video and thumbnail to YouTube."""
    from vidmation.services.youtube.uploader import YouTubeUploader

    if ctx.final_video_path is None:
        raise RuntimeError("stage_upload requires ctx.final_video_path")
    if ctx.script is None:
        raise RuntimeError("stage_upload requires ctx.script")

    logger.info("[upload] Uploading video to YouTube")

    uploader = YouTubeUploader(settings=settings)

    yt_config = ctx.channel_profile.youtube

    result = uploader.upload(
        video_path=ctx.final_video_path,
        title=ctx.script.get("title", ctx.topic),
        description=ctx.script.get("description", ""),
        tags=ctx.script.get("tags", []),
        category_id=yt_config.category_id,
        visibility=yt_config.visibility,
        thumbnail_path=ctx.thumbnail_path,
    )

    logger.info(
        "[upload] Uploaded — YouTube ID: %s, URL: %s",
        result.get("video_id"),
        result.get("url"),
    )


# ---------------------------------------------------------------------------
# Stage registry (name -> callable) — used by the orchestrator
# ---------------------------------------------------------------------------

STAGE_REGISTRY: list[tuple[str, callable]] = [
    ("script_generation", stage_script_generation),
    ("tts", stage_tts),
    ("captions", stage_captions),
    ("media_sourcing", stage_media_sourcing),
    ("video_assembly", stage_video_assembly),
    ("thumbnail", stage_thumbnail),
    ("upload", stage_upload),
]
"""Ordered list of ``(stage_name, stage_function)`` tuples."""
