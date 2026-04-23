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
    from aividio.config.settings import Settings
    from aividio.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Script generation
# ---------------------------------------------------------------------------

def stage_script_generation(ctx: PipelineContext, settings: Settings) -> None:
    """Generate a structured video script from the topic and channel profile."""
    from aividio.services.scriptgen import create_script_generator

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
    from aividio.services.tts import create_tts_provider

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
    from aividio.services.captions.whisper import WhisperCaptionGenerator

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
# 3b. Background music selection
# ---------------------------------------------------------------------------

def stage_music_selection(ctx: PipelineContext, settings: Settings) -> None:
    """Select or download background music for the video.

    Uses the channel profile's ``music.genre`` to pick an appropriate track.
    Checks ``assets/music/`` for local files first, then downloads a
    royalty-free track from the bundled catalog if needed.

    Sets ``ctx.music_path`` so the video assembly stage can mix it with
    the voiceover.
    """
    from aividio.services.music.selector import MusicSelector

    logger.info("[music] Selecting background music (genre=%s)", ctx.channel_profile.music.genre)

    selector = MusicSelector(assets_dir=settings.assets_dir)
    music_path = selector.select_music(
        profile=ctx.channel_profile,
        work_dir=ctx.work_dir,
    )

    if music_path is not None:
        ctx.music_path = Path(music_path)
        logger.info("[music] Background music selected: %s", ctx.music_path)
    else:
        logger.warning("[music] No background music available — video will have voiceover only")


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
    from aividio.services.models.orchestrator import ModelOrchestrator

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

def _build_query_variations(section: dict, max_queries: int = 3) -> list[str]:
    """Generate 2-3 search query variations for a single script section.

    Real faceless YouTube videos cut between visuals every 3-5 seconds, so
    we need multiple clips per section.  Different query phrasings avoid
    getting near-duplicate results from the stock provider.

    The first query is always the section's ``visual_query`` (authored by
    the script generator).  Additional queries are derived from the section
    ``heading`` and keywords extracted from the ``narration``.
    """
    queries: list[str] = []

    # 1. Primary query — always the visual_query from the script
    primary = section.get("visual_query", "").strip()
    if primary:
        queries.append(primary)

    # 2. Heading-based variation (if it differs from the primary)
    heading = section.get("heading", "").strip()
    if heading and heading.lower() != primary.lower():
        queries.append(heading)

    # 3. Keywords from the narration text — pick a few content words
    if len(queries) < max_queries:
        narration = section.get("narration", section.get("text", ""))
        if narration:
            # Simple keyword extraction: take longer words, skip stop words
            _stop = {
                "the", "a", "an", "is", "are", "was", "were", "be", "been",
                "being", "have", "has", "had", "do", "does", "did", "will",
                "would", "could", "should", "may", "might", "can", "shall",
                "to", "of", "in", "for", "on", "with", "at", "by", "from",
                "as", "into", "through", "during", "before", "after", "and",
                "but", "or", "nor", "not", "so", "yet", "both", "either",
                "neither", "this", "that", "these", "those", "it", "its",
                "they", "them", "their", "we", "our", "you", "your", "he",
                "she", "his", "her", "who", "which", "what", "where", "when",
                "how", "all", "each", "every", "any", "few", "more", "most",
                "some", "such", "than", "too", "very", "just", "about",
            }
            words = [
                w.strip(".,;:!?\"'()-")
                for w in narration.split()
                if len(w) > 4 and w.lower().strip(".,;:!?\"'()-") not in _stop
            ]
            # Pick 3-4 unique content words for a keyword query
            seen: set[str] = set()
            keywords: list[str] = []
            for w in words:
                lower = w.lower()
                if lower not in seen:
                    seen.add(lower)
                    keywords.append(w)
                if len(keywords) >= 4:
                    break
            if keywords:
                queries.append(" ".join(keywords))

    # Ensure at least 1 query even if visual_query was empty
    if not queries:
        fallback = section.get("heading", section.get("narration", "stock footage")[:60])
        queries.append(fallback)

    return queries[:max_queries]


def stage_media_sourcing(ctx: PipelineContext, settings: Settings) -> None:
    """Download stock media for each script section — multiple clips per section.

    For each section, this stage downloads 3-6 clips (a mix of videos and
    images) using varied search queries derived from the section's
    ``visual_query``, ``heading``, and ``narration`` keywords.  This produces
    the visual variety needed for faceless YouTube videos where the visuals
    should cut every 3-5 seconds.

    If ``stage_ai_video_generation`` has already run (in ``"ai"`` or
    ``"mixed"`` mode), this stage will skip sections that already have
    AI-generated clips and only source stock media for the remaining ones.

    The resulting ``ctx.media_clips`` entries contain both:
    - ``"path"``  — the first clip (backward-compatible single path)
    - ``"paths"`` — a list of all clip paths for multi-clip assembly
    """
    from aividio.services.media import create_media_provider

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
        "[media] Sourcing multi-clip stock media for %d/%d sections",
        len(sections_needing_stock),
        len(sections),
    )

    media_provider = create_media_provider(settings=settings)
    clips: list[dict] = list(ctx.media_clips or [])
    existing_indices = {c["section_index"] for c in clips}

    # Target 4 clips per section (yields ~3-5 second sub-clips for typical
    # 15-30 second sections).  The provider may return fewer if results are
    # scarce.
    clips_per_section = 4

    for section in sections_needing_stock:
        idx = section["section_number"]
        if idx in existing_indices:
            continue

        visual_type = section.get("visual_type", "video")
        queries = _build_query_variations(section)

        logger.info(
            "[media] Section %d: queries=%r type=%s clips_target=%d",
            idx, queries, visual_type, clips_per_section,
        )

        results = media_provider.search_and_download_multiple(
            queries=queries,
            media_type=visual_type,
            output_dir=ctx.work_dir / "media",
            section_index=idx,
            clips_per_section=clips_per_section,
        )

        all_paths = [str(r["path"]) for r in results]
        sources = list({r.get("source", "unknown") for r in results})
        attributions = [r.get("attribution", "") for r in results if r.get("attribution")]

        clips.append({
            "path": all_paths[0],               # backward compat: first clip
            "paths": all_paths,                  # NEW: all clips for this section
            "section_index": idx,
            "type": visual_type,
            "source": ", ".join(sources),
            "attribution": "; ".join(attributions),
            "clip_count": len(all_paths),
        })

    ctx.media_clips = sorted(clips, key=lambda c: c["section_index"])

    total_clips = sum(c.get("clip_count", 1) for c in ctx.media_clips)
    logger.info(
        "[media] Total media entries: %d sections, %d individual clips",
        len(ctx.media_clips),
        total_clips,
    )


# ---------------------------------------------------------------------------
# 5. Video assembly (FFmpeg composition)
# ---------------------------------------------------------------------------

def stage_video_assembly(ctx: PipelineContext, settings: Settings) -> None:
    """Assemble voiceover, media clips, captions, and music into the final video."""
    from aividio.utils.files import get_output_path

    if ctx.voiceover_path is None:
        raise RuntimeError("stage_video_assembly requires ctx.voiceover_path")
    if ctx.media_clips is None:
        raise RuntimeError("stage_video_assembly requires ctx.media_clips")

    logger.info("[assembly] Assembling final video")

    from aividio.utils.files import get_work_dir
    from aividio.video.assembler import VideoAssembler

    output_path = get_output_path(ctx.video_id, "final.mp4")
    work_dir = get_work_dir(ctx.video_id)

    assembler = VideoAssembler(
        video_config=ctx.channel_profile.video,
        work_dir=work_dir,
    )

    # Merge script sections with media clip paths from ctx.media_clips.
    # The assembler expects each section to have a "media_path" key.
    # When multi-clip sourcing is active, sections also get "media_paths"
    # (list of paths) so the assembler can interleave sub-clips.
    sections = ctx.script.get("sections", []) if ctx.script else []
    clip_by_index = {c["section_index"]: c for c in (ctx.media_clips or [])}

    enriched_sections: list[dict] = []
    for sec in sections:
        idx = sec["section_number"]
        clip_info = clip_by_index.get(idx)
        if clip_info is None:
            logger.warning("[assembly] No media clip for section %d — skipping", idx)
            continue
        enriched = dict(sec)
        enriched["media_path"] = clip_info["path"]
        # Pass multi-clip paths if available
        if clip_info.get("paths") and len(clip_info["paths"]) > 1:
            enriched["media_paths"] = clip_info["paths"]
        enriched_sections.append(enriched)

    if not enriched_sections:
        raise RuntimeError(
            "No sections have media clips — cannot assemble video. "
            f"Script has {len(sections)} sections, media_clips has {len(ctx.media_clips)} entries."
        )

    ctx.final_video_path = assembler.assemble(
        sections=enriched_sections,
        voiceover_path=ctx.voiceover_path,
        word_timestamps=ctx.word_timestamps or [],
        music_path=ctx.music_path,
        output_path=output_path,
    )

    logger.info("[assembly] Final video saved to %s", ctx.final_video_path)


# ---------------------------------------------------------------------------
# 6. Thumbnail generation
# ---------------------------------------------------------------------------

def stage_thumbnail(ctx: PipelineContext, settings: Settings) -> None:
    """Generate a thumbnail image for the video."""
    from aividio.services.imagegen import create_image_generator

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
    """Upload the finished video and thumbnail to YouTube.

    Uses AI-generated metadata (title, description with chapters, tags)
    when available, and uploads companion SRT captions if present.
    Supports scheduled publishing via the channel profile.

    Credential resolution order:
    1. Per-channel OAuth token stored in the channel's DB record
       (multi-channel SaaS mode).
    2. Global token file at ``data/youtube_token.json`` (legacy single-
       channel mode).
    """
    from aividio.services.youtube.auth import (
        get_credentials,
        get_credentials_for_channel,
    )
    from aividio.services.youtube.uploader import YouTubeUploader

    if ctx.final_video_path is None:
        raise RuntimeError("stage_upload requires ctx.final_video_path")
    if ctx.script is None:
        raise RuntimeError("stage_upload requires ctx.script")

    logger.info("[upload] Uploading video to YouTube")

    # Resolve OAuth credentials — prefer per-channel DB token, then
    # fall back to the legacy global token file.
    client_secret_path = settings.data_dir / "client_secret.json"
    credentials = None

    # Try per-channel credentials (multi-channel SaaS mode)
    channel_id = getattr(ctx, "channel_id", None)
    if channel_id:
        try:
            from aividio.db.engine import get_session
            from aividio.db.repos import ChannelRepo

            session = get_session()
            repo = ChannelRepo(session)
            channel = repo.get(channel_id)
            session.close()

            if channel and channel.oauth_token_json:
                credentials = get_credentials_for_channel(
                    channel_id=channel_id,
                    client_secret_path=client_secret_path,
                )
                logger.info(
                    "[upload] Using per-channel credentials for %s",
                    channel.name,
                )
        except Exception as exc:
            logger.warning(
                "[upload] Could not load per-channel credentials (%s); "
                "falling back to global token",
                exc,
            )
            credentials = None

    # Fall back to global token file
    if credentials is None:
        token_path = settings.data_dir / "youtube_token.json"

        if not token_path.exists():
            logger.warning(
                "[upload] YouTube token not found at %s — skipping upload. "
                "Run 'aividio youtube setup' to configure.",
                token_path,
            )
            return

        credentials = get_credentials(
            token_path=token_path,
            client_secret_path=client_secret_path,
        )

    uploader = YouTubeUploader(credentials=credentials)
    yt_config = ctx.channel_profile.youtube

    # Generate AI-optimized metadata
    title = ctx.script.get("title", ctx.topic)
    description = ctx.script.get("description", "")
    tags = ctx.script.get("tags", [])

    try:
        from aividio.services.youtube.metadata import YouTubeMetadataGenerator

        meta_gen = YouTubeMetadataGenerator(settings=settings)
        metadata = meta_gen.generate(
            script=ctx.script,
            channel_profile=ctx.channel_profile,
        )
        title = metadata.get("title", title)
        description = metadata.get("description", description)
        tags = metadata.get("tags", tags)
        logger.info("[upload] AI metadata generated: title=%r", title)
    except Exception as exc:
        logger.warning("[upload] AI metadata generation failed (%s), using script defaults", exc)

    # Parse schedule from profile
    publish_at = None
    if yt_config.schedule:
        try:
            from aividio.cli.youtube import _parse_schedule

            publish_at = _parse_schedule(yt_config.schedule)
            logger.info("[upload] Scheduled publish at %s", publish_at.isoformat())
        except Exception as exc:
            logger.warning("[upload] Could not parse schedule %r: %s", yt_config.schedule, exc)

    # Upload video
    if publish_at:
        video_id = uploader.upload_with_schedule(
            video_path=ctx.final_video_path,
            title=title,
            description=description,
            tags=tags,
            category_id=yt_config.category_id,
            thumbnail_path=ctx.thumbnail_path,
            publish_at=publish_at,
        )
    else:
        video_id = uploader.upload(
            video_path=ctx.final_video_path,
            title=title,
            description=description,
            tags=tags,
            category_id=yt_config.category_id,
            visibility=yt_config.visibility,
            thumbnail_path=ctx.thumbnail_path,
        )

    logger.info("[upload] Uploaded — YouTube video_id=%s", video_id)

    # Upload SRT captions if available
    srt_path = ctx.final_video_path.with_suffix(".srt")
    if srt_path.exists():
        try:
            uploader.upload_captions(
                video_id=video_id,
                srt_path=srt_path,
                language=yt_config.default_language,
                name="Auto-generated",
            )
            logger.info("[upload] Captions uploaded from %s", srt_path.name)
        except Exception as exc:
            logger.warning("[upload] Caption upload failed: %s", exc)


# ---------------------------------------------------------------------------
# Stage registry (name -> callable) — used by the orchestrator
# ---------------------------------------------------------------------------

STAGE_REGISTRY: list[tuple[str, callable]] = [
    ("script_generation", stage_script_generation),
    ("tts", stage_tts),
    ("captions", stage_captions),
    ("music_selection", stage_music_selection),
    ("ai_video_generation", stage_ai_video_generation),
    ("media_sourcing", stage_media_sourcing),
    ("video_assembly", stage_video_assembly),
    ("thumbnail", stage_thumbnail),
    ("upload", stage_upload),
]
"""Ordered list of ``(stage_name, stage_function)`` tuples.

``music_selection`` runs after ``captions`` but before video generation/sourcing
so that background music is ready when the assembler composes the final video.

``ai_video_generation`` runs before ``media_sourcing`` so that AI-generated
clips are available when the stock sourcing stage decides which sections
still need media.
"""
