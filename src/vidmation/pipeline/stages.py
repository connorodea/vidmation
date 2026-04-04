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

    # synthesize() returns (audio_path: Path, duration: float)
    voiceover_path, voiceover_duration = tts.synthesize(
        text=full_narration,
        output_path=output_path,
        voice_config=ctx.channel_profile.voice,
    )

    ctx.voiceover_path = Path(voiceover_path)
    ctx.voiceover_duration = voiceover_duration

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
    # transcribe() returns list[dict] directly (word-level timestamps)
    ctx.word_timestamps = captioner.transcribe(audio_path=ctx.voiceover_path)

    # Persist timestamps
    ts_path = ctx.work_dir / "word_timestamps.json"
    ts_path.write_text(json.dumps(ctx.word_timestamps, indent=2), encoding="utf-8")

    logger.info(
        "[captions] Generated %d timestamp entries",
        len(ctx.word_timestamps),
    )


# ---------------------------------------------------------------------------
# 4a. AI video generation (uses ModelOrchestrator for multi-model routing)
# ---------------------------------------------------------------------------

def stage_ai_video_generation(ctx: PipelineContext, settings: Settings) -> None:
    """Generate AI video clips for script sections using the ModelOrchestrator.

    Behaviour depends on ``media_source`` in the channel profile or script:

    * ``"ai"``    — Use AI generation for *all* sections.
    * ``"mixed"`` — Use AI for sections with ``visual_type`` containing
      ``"ai_image"`` or ``"ai_video"``; fall back to stock for others.
    * ``"stock"`` — Skip AI generation entirely (existing behaviour).

    The ``media_source`` is read from (in priority order):
    1. ``ctx.script["media_source"]`` (set by the script generator)
    2. Profile-level override via ``ctx.channel_profile.content`` extra attrs
    3. Default: ``"stock"`` (preserves backward compatibility)
    """
    from vidmation.services.models.orchestrator import ModelOrchestrator

    if ctx.script is None:
        raise RuntimeError("stage_ai_video_generation requires ctx.script")

    # Determine media source strategy
    media_source = (
        ctx.script.get("media_source")
        or getattr(ctx.channel_profile.content, "media_source", None)
        or "stock"
    ).lower()

    if media_source == "stock":
        logger.info("[ai_video] media_source=stock — skipping AI video generation")
        return

    sections = ctx.script.get("sections", [])
    if not sections:
        logger.warning("[ai_video] No sections in script — nothing to generate")
        return

    # Filter sections based on strategy
    if media_source == "mixed":
        ai_sections = [
            s for s in sections
            if s.get("visual_type", "").lower() in ("ai_image", "ai_video", "ai")
        ]
        logger.info(
            "[ai_video] media_source=mixed — %d/%d sections use AI generation",
            len(ai_sections),
            len(sections),
        )
    else:
        # "ai" — generate for all sections
        ai_sections = sections
        logger.info(
            "[ai_video] media_source=ai — generating AI video for all %d sections",
            len(ai_sections),
        )

    if not ai_sections:
        logger.info("[ai_video] No AI-eligible sections found in mixed mode")
        return

    output_dir = ctx.work_dir / "ai_clips"
    output_dir.mkdir(parents=True, exist_ok=True)

    orchestrator = ModelOrchestrator(settings=settings)

    # Log cost estimate before generating
    cost_info = orchestrator.estimate_total_cost(ai_sections)
    logger.info(
        "[ai_video] Estimated cost: $%.4f across %d models",
        cost_info["total_usd"],
        cost_info["model_count"],
    )
    for sc in cost_info["sections"]:
        logger.info(
            "[ai_video]   Section %d: %s via %s ($%.4f)",
            sc["section_number"],
            sc["category"],
            sc["model"],
            sc["estimated_cost_usd"],
        )

    # Generate clips
    results = orchestrator.generate_batch(
        sections=ai_sections,
        profile=ctx.channel_profile,
        output_dir=output_dir,
        parallel=len(ai_sections) > 1,
    )

    # Merge AI clips into the media_clips list.  If media_clips already has
    # entries (e.g. from a prior stock-sourcing pass in mixed mode), replace
    # matching section indices; otherwise initialise the list.
    existing_clips = {c["section_index"]: c for c in (ctx.media_clips or [])}

    for result in results:
        existing_clips[result["section_index"]] = result

    # Rebuild the list in section order
    ctx.media_clips = sorted(existing_clips.values(), key=lambda c: c["section_index"])

    total_cost = sum(r.get("cost", 0) for r in results)
    logger.info(
        "[ai_video] Generated %d AI clips (actual cost: ~$%.4f)",
        len(results),
        total_cost,
    )


# ---------------------------------------------------------------------------
# 4b. Media sourcing (stock video/images per script section)
# ---------------------------------------------------------------------------

def stage_media_sourcing(ctx: PipelineContext, settings: Settings) -> None:
    """Download stock media or generate AI images for each script section.

    If ``stage_ai_video_generation`` has already run (in ``"ai"`` or
    ``"mixed"`` mode), this stage will skip sections that already have
    AI-generated clips and only source stock media for the remaining ones.
    """
    from vidmation.services.media import create_media_provider

    if ctx.script is None:
        raise RuntimeError("stage_media_sourcing requires ctx.script")

    # Determine which sections still need media
    ai_covered_indices: set[int] = set()
    if ctx.media_clips:
        ai_covered_indices = {
            c["section_index"]
            for c in ctx.media_clips
            if c.get("type") == "ai_video"
        }

    sections = ctx.script.get("sections", [])
    sections_needing_stock = [
        s for s in sections
        if s["section_number"] not in ai_covered_indices
    ]

    if not sections_needing_stock:
        logger.info(
            "[media] All %d sections already covered by AI generation — skipping stock sourcing",
            len(sections),
        )
        return

    logger.info(
        "[media] Sourcing stock media for %d/%d sections",
        len(sections_needing_stock),
        len(sections),
    )

    media_provider = create_media_provider(settings=settings)
    clips: list[dict] = list(ctx.media_clips or [])
    existing_indices = {c["section_index"] for c in clips}

    for section in sections_needing_stock:
        idx = section["section_number"]
        if idx in existing_indices:
            continue

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

    ctx.media_clips = sorted(clips, key=lambda c: c["section_index"])

    logger.info("[media] Total media clips after stock sourcing: %d", len(ctx.media_clips))


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

    # generate() returns a Path directly
    ctx.thumbnail_path = Path(generator.generate(
        prompt=f"YouTube thumbnail for: {title}. Style: {thumbnail_config.style}",
        output_path=ctx.work_dir / "thumbnail.png",
    ))

    logger.info("[thumbnail] Saved to %s", ctx.thumbnail_path)


# ---------------------------------------------------------------------------
# 7. YouTube upload
# ---------------------------------------------------------------------------

def stage_upload(ctx: PipelineContext, settings: Settings) -> None:
    """Upload the finished video and thumbnail to YouTube."""
    from vidmation.services.youtube.auth import get_credentials
    from vidmation.services.youtube.uploader import YouTubeUploader

    if ctx.final_video_path is None:
        raise RuntimeError("stage_upload requires ctx.final_video_path")
    if ctx.script is None:
        raise RuntimeError("stage_upload requires ctx.script")

    logger.info("[upload] Uploading video to YouTube")

    # Resolve OAuth credentials from disk (token cached next to work_dir)
    token_path = settings.data_dir / "youtube_token.json"
    client_secret_path = settings.data_dir / "client_secret.json"
    credentials = get_credentials(
        token_path=token_path,
        client_secret_path=client_secret_path,
    )

    uploader = YouTubeUploader(credentials=credentials)

    yt_config = ctx.channel_profile.youtube

    video_id = uploader.upload(
        video_path=ctx.final_video_path,
        title=ctx.script.get("title", ctx.topic),
        description=ctx.script.get("description", ""),
        tags=ctx.script.get("tags", []),
        category_id=yt_config.category_id,
        visibility=yt_config.visibility,
        thumbnail_path=ctx.thumbnail_path,
    )

    logger.info("[upload] Uploaded — YouTube video_id=%s", video_id)


# ---------------------------------------------------------------------------
# Stage registry (name -> callable) — used by the orchestrator
# ---------------------------------------------------------------------------

STAGE_REGISTRY: list[tuple[str, callable]] = [
    ("script_generation", stage_script_generation),
    ("tts", stage_tts),
    ("captions", stage_captions),
    ("ai_video_generation", stage_ai_video_generation),
    ("media_sourcing", stage_media_sourcing),
    ("video_assembly", stage_video_assembly),
    ("thumbnail", stage_thumbnail),
    ("upload", stage_upload),
]
"""Ordered list of ``(stage_name, stage_function)`` tuples.

``ai_video_generation`` runs before ``media_sourcing`` so that AI-generated
clips are available when the stock sourcing stage decides which sections
still need media.
"""
