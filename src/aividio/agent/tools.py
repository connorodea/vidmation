"""Tool implementations for the AI agent orchestrator.

Each tool wraps an existing AIVIDIO service, providing a clean interface
for the Claude agent to call.  Tools handle errors gracefully and return
descriptive results that the agent can reason about.
"""

from __future__ import annotations

import json
import logging
import traceback
from pathlib import Path
from typing import Any

from aividio.analytics.tracker import UsageTracker, get_tracker
from aividio.config.profiles import ChannelProfile
from aividio.config.settings import Settings
from aividio.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


# ── Niche-to-caption-template mapping ────────────────────────────────────────

NICHE_TEMPLATE_MAP: dict[str, str] = {
    "finance": "finance_serious",
    "tech": "tech_modern",
    "meditation": "meditation_calm",
    "spirituality": "meditation_calm",
    "education": "education_clear",
    "motivation": "motivation_fire",
    "gaming": "gaming_hype",
    "storytelling": "storytelling",
    "news": "news_anchor",
    "comedy": "tiktok_viral",
    "health": "education_clear",
    "science": "tech_modern",
    "crypto": "finance_serious",
    "fitness": "motivation_fire",
    "travel": "storytelling",
    "food": "tiktok_viral",
    "history": "storytelling",
    "psychology": "education_clear",
    "business": "finance_serious",
    "self-improvement": "motivation_fire",
}


class AgentToolkit:
    """Collection of tools available to the AI agent.

    Each method maps directly to a tool the Claude agent can call via
    tool_use.  Methods return a descriptive string result that is fed
    back into the conversation so the agent can reason about what
    happened.
    """

    def __init__(
        self,
        settings: Settings,
        profile: ChannelProfile,
        ctx: PipelineContext,
    ) -> None:
        self.settings = settings
        self.profile = profile
        self.ctx = ctx
        self.tracker: UsageTracker = get_tracker()
        self._total_cost: float = 0.0

    @property
    def total_cost(self) -> float:
        return self._total_cost

    # ------------------------------------------------------------------
    # 1. Script generation
    # ------------------------------------------------------------------

    def generate_script(
        self,
        topic: str,
        style: str = "listicle",
        target_duration_minutes: int = 10,
    ) -> str:
        """Generate a complete video script using Claude."""
        try:
            from aividio.services.scriptgen import create_script_generator

            generator = create_script_generator(settings=self.settings)
            script = generator.generate(topic=topic, profile=self.profile)
            self.ctx.script = script

            # Persist to disk
            script_path = self.ctx.work_dir / "script.json"
            script_path.write_text(json.dumps(script, indent=2), encoding="utf-8")

            section_count = len(script.get("sections", []))
            title = script.get("title", "Untitled")
            est_duration = script.get("total_estimated_duration_seconds", 0)

            self._track("claude", "script_generation", input_tokens=2000, output_tokens=4000)

            return (
                f"Script generated successfully.\n"
                f"Title: {title}\n"
                f"Sections: {section_count}\n"
                f"Estimated duration: {est_duration}s ({est_duration / 60:.1f} min)\n"
                f"Hook: {script.get('hook', 'N/A')[:150]}\n"
                f"Saved to: {script_path}"
            )
        except Exception as exc:
            return f"ERROR generating script: {exc}\n{traceback.format_exc()}"

    # ------------------------------------------------------------------
    # 2. TTS voiceover
    # ------------------------------------------------------------------

    def generate_voiceover(self, provider: str = "elevenlabs") -> str:
        """Generate TTS voiceover from script."""
        try:
            from aividio.services.tts import create_tts_provider

            if self.ctx.script is None:
                return "ERROR: No script available. Run generate_script first."

            tts = create_tts_provider(provider=provider, settings=self.settings)

            # Build full narration from script parts
            parts: list[str] = []
            if self.ctx.script.get("hook"):
                parts.append(self.ctx.script["hook"])
            for section in self.ctx.script.get("sections", []):
                parts.append(section.get("narration", section.get("text", "")))
            if self.ctx.script.get("outro"):
                parts.append(self.ctx.script["outro"])

            full_narration = "\n\n".join(parts)
            output_path = self.ctx.work_dir / "voiceover.mp3"

            voiceover_path, voiceover_duration = tts.synthesize(
                text=full_narration,
                output_path=output_path,
                voice_config=self.profile.voice,
            )

            self.ctx.voiceover_path = Path(voiceover_path)
            self.ctx.voiceover_duration = voiceover_duration

            self._track(
                provider, "tts_synthesis",
                characters=len(full_narration),
            )

            return (
                f"Voiceover generated successfully.\n"
                f"Provider: {provider}\n"
                f"Duration: {voiceover_duration:.1f}s ({voiceover_duration / 60:.1f} min)\n"
                f"Characters: {len(full_narration)}\n"
                f"Saved to: {voiceover_path}"
            )
        except Exception as exc:
            return f"ERROR generating voiceover: {exc}\n{traceback.format_exc()}"

    # ------------------------------------------------------------------
    # 3. Audio transcription
    # ------------------------------------------------------------------

    def transcribe_audio(self) -> str:
        """Get word-level timestamps from voiceover using Whisper."""
        try:
            from aividio.services.captions.whisper import WhisperCaptionGenerator

            if self.ctx.voiceover_path is None:
                return "ERROR: No voiceover available. Run generate_voiceover first."

            captioner = WhisperCaptionGenerator(settings=self.settings)
            self.ctx.word_timestamps = captioner.transcribe(
                audio_path=self.ctx.voiceover_path
            )

            ts_path = self.ctx.work_dir / "word_timestamps.json"
            ts_path.write_text(
                json.dumps(self.ctx.word_timestamps, indent=2), encoding="utf-8"
            )

            self._track(
                "whisper_replicate", "transcription",
                duration_seconds=self.ctx.voiceover_duration or 0,
            )

            return (
                f"Transcription complete.\n"
                f"Word-level timestamps: {len(self.ctx.word_timestamps)} words\n"
                f"Saved to: {ts_path}"
            )
        except Exception as exc:
            return f"ERROR transcribing audio: {exc}\n{traceback.format_exc()}"

    # ------------------------------------------------------------------
    # 4. Stock media search
    # ------------------------------------------------------------------

    def search_stock_media(
        self,
        query: str,
        media_type: str = "video",
        count: int = 3,
    ) -> str:
        """Search and download stock media from Pexels/Pixabay."""
        try:
            from aividio.services.media import create_media_provider

            media_provider = create_media_provider(settings=self.settings)
            output_dir = self.ctx.work_dir / "media"
            output_dir.mkdir(parents=True, exist_ok=True)

            # For batch stock sourcing of all script sections
            if self.ctx.script and query == "__all_sections__":
                return self._source_all_stock_media(media_provider, output_dir)

            result = media_provider.search_and_download(
                query=query,
                media_type=media_type,
                output_dir=output_dir,
                section_index=0,
            )

            self._track("pexels", "stock_search")

            return (
                f"Stock media found and downloaded.\n"
                f"Query: {query}\n"
                f"Type: {media_type}\n"
                f"Source: {result.get('source', 'unknown')}\n"
                f"Path: {result.get('path', 'N/A')}"
            )
        except Exception as exc:
            return f"ERROR searching stock media: {exc}\n{traceback.format_exc()}"

    def _source_all_stock_media(
        self, media_provider: Any, output_dir: Path
    ) -> str:
        """Source stock media for all script sections."""
        if not self.ctx.script:
            return "ERROR: No script to source media for."

        sections = self.ctx.script.get("sections", [])
        clips: list[dict] = list(self.ctx.media_clips or [])
        existing_indices = {c["section_index"] for c in clips}
        downloaded = 0

        for section in sections:
            idx = section["section_number"]
            if idx in existing_indices:
                continue

            query = section.get("visual_query", "")
            visual_type = section.get("visual_type", "video")

            try:
                result = media_provider.search_and_download(
                    query=query,
                    media_type=visual_type,
                    output_dir=output_dir,
                    section_index=idx,
                )
                clips.append({
                    "path": str(result["path"]),
                    "section_index": idx,
                    "type": visual_type,
                    "source": result.get("source", "unknown"),
                    "attribution": result.get("attribution", ""),
                })
                downloaded += 1
            except Exception as exc:
                logger.warning("Failed to source media for section %d: %s", idx, exc)

        self.ctx.media_clips = sorted(clips, key=lambda c: c["section_index"])
        self._track("pexels", "stock_batch_search")

        return (
            f"Stock media sourced for {downloaded}/{len(sections)} sections.\n"
            f"Total media clips: {len(self.ctx.media_clips)}"
        )

    # ------------------------------------------------------------------
    # 5. AI video generation
    # ------------------------------------------------------------------

    def generate_ai_video(
        self,
        prompt: str,
        model: str = "auto",
        duration: float = 5.0,
        section_index: int = 0,
    ) -> str:
        """Generate AI video clip using ModelOrchestrator."""
        try:
            from aividio.services.models.orchestrator import ModelOrchestrator

            orchestrator = ModelOrchestrator(settings=self.settings)
            output_dir = self.ctx.work_dir / "ai_clips"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Build a section dict for the orchestrator
            section = {
                "visual_query": prompt,
                "visual_type": "ai_video" if model == "auto" else model,
                "duration": duration,
                "section_number": section_index,
            }

            result = orchestrator.generate_for_section(
                section=section,
                profile=self.profile,
                output_dir=output_dir,
            )

            # Track in media clips
            clips = list(self.ctx.media_clips or [])
            clips.append({
                "path": str(result),
                "section_index": section_index,
                "type": "ai_video",
                "source": model,
            })
            self.ctx.media_clips = sorted(clips, key=lambda c: c["section_index"])

            self._track(
                "replicate_kling", "ai_video_generation",
                duration_seconds=duration,
            )

            return (
                f"AI video clip generated.\n"
                f"Model: {model}\n"
                f"Duration: {duration}s\n"
                f"Prompt: {prompt[:100]}\n"
                f"Output: {result}"
            )
        except Exception as exc:
            return f"ERROR generating AI video: {exc}\n{traceback.format_exc()}"

    # ------------------------------------------------------------------
    # 6. AI image generation
    # ------------------------------------------------------------------

    def generate_ai_image(
        self,
        prompt: str,
        provider: str = "dalle",
        section_index: int = 0,
    ) -> str:
        """Generate an AI image."""
        try:
            from aividio.services.imagegen import create_image_generator

            generator = create_image_generator(provider=provider, settings=self.settings)
            output_path = self.ctx.work_dir / "media" / f"ai_image_{section_index:03d}.png"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            result_path = Path(generator.generate(
                prompt=prompt,
                output_path=output_path,
            ))

            self._track(provider, "image_generation", images=1)

            return (
                f"AI image generated.\n"
                f"Provider: {provider}\n"
                f"Prompt: {prompt[:100]}\n"
                f"Output: {result_path}"
            )
        except Exception as exc:
            return f"ERROR generating AI image: {exc}\n{traceback.format_exc()}"

    # ------------------------------------------------------------------
    # 7. Video assembly
    # ------------------------------------------------------------------

    def assemble_video(self) -> str:
        """Assemble all components into final video."""
        try:
            from aividio.utils.files import get_output_path, get_work_dir
            from aividio.video.assembler import VideoAssembler

            if self.ctx.voiceover_path is None:
                return "ERROR: No voiceover available. Run generate_voiceover first."
            if not self.ctx.media_clips:
                return "ERROR: No media clips available. Run stock/AI media sourcing first."

            output_path = get_output_path(self.ctx.video_id, "final.mp4")
            work_dir = get_work_dir(self.ctx.video_id)

            assembler = VideoAssembler(
                video_config=self.profile.video,
                work_dir=work_dir,
            )

            sections = self.ctx.script.get("sections", []) if self.ctx.script else []

            self.ctx.final_video_path = assembler.assemble(
                sections=sections,
                voiceover_path=self.ctx.voiceover_path,
                word_timestamps=self.ctx.word_timestamps or [],
                music_path=self.ctx.music_path,
                output_path=output_path,
            )

            return (
                f"Video assembled successfully.\n"
                f"Output: {self.ctx.final_video_path}\n"
                f"Sections: {len(sections)}\n"
                f"Has captions: {bool(self.ctx.word_timestamps)}"
            )
        except Exception as exc:
            return f"ERROR assembling video: {exc}\n{traceback.format_exc()}"

    # ------------------------------------------------------------------
    # 8. Captions
    # ------------------------------------------------------------------

    def apply_captions(self, template: str = "auto") -> str:
        """Add animated captions to video.

        If template is "auto", selects based on the channel niche.
        """
        try:
            from aividio.captions.templates import get_template

            if self.ctx.final_video_path is None:
                return "ERROR: No video to apply captions to. Run assemble_video first."
            if not self.ctx.word_timestamps:
                return "ERROR: No word timestamps. Run transcribe_audio first."

            # Auto-select template based on niche
            if template == "auto":
                niche = self.profile.niche.lower()
                template = NICHE_TEMPLATE_MAP.get(niche, "bold_centered")

            # Verify template exists
            try:
                caption_template = get_template(template)
            except (KeyError, ValueError):
                logger.warning("Template %r not found, falling back to bold_centered", template)
                template = "bold_centered"
                caption_template = get_template(template)

            from aividio.video.captions_render import burn_captions, generate_ass_file

            ass_path = self.ctx.work_dir / "captions.ass"
            generate_ass_file(
                word_timestamps=self.ctx.word_timestamps,
                template=caption_template,
                output_path=ass_path,
            )

            output_path = self.ctx.work_dir / "final_captioned.mp4"
            captioned_path = burn_captions(
                video_path=self.ctx.final_video_path,
                ass_path=ass_path,
                output_path=output_path,
            )

            self.ctx.final_video_path = captioned_path

            return (
                f"Captions applied successfully.\n"
                f"Template: {template} ({caption_template.display_name})\n"
                f"Words: {len(self.ctx.word_timestamps)}\n"
                f"Output: {captioned_path}"
            )
        except Exception as exc:
            return f"ERROR applying captions: {exc}\n{traceback.format_exc()}"

    # ------------------------------------------------------------------
    # 9. Magic Zoom
    # ------------------------------------------------------------------

    def apply_magic_zoom(self, style: str = "smooth", max_zooms: int = 8) -> str:
        """Add auto-zoom effects at emphasis points."""
        try:
            from aividio.effects.magic_zoom import MagicZoom

            if self.ctx.final_video_path is None:
                return "ERROR: No video available."
            if not self.ctx.word_timestamps:
                return "ERROR: No word timestamps for emphasis detection."

            zoom_engine = MagicZoom(settings=self.settings)

            # Detect emphasis points
            zoom_points = zoom_engine.detect_emphasis_points(
                word_timestamps=self.ctx.word_timestamps,
                script=self.ctx.script,
                max_zooms=max_zooms,
            )

            if not zoom_points:
                return "No emphasis points detected for zoom effects. Skipping."

            output_path = self.ctx.work_dir / "final_zoomed.mp4"
            zoomed_path = zoom_engine.apply_zooms(
                video_path=self.ctx.final_video_path,
                zoom_points=zoom_points,
                output_path=output_path,
            )

            self.ctx.final_video_path = zoomed_path

            self._track("claude", "magic_zoom_analysis", input_tokens=1000, output_tokens=500)

            return (
                f"Magic zoom applied.\n"
                f"Zoom points: {len(zoom_points)}\n"
                f"Style: {style}\n"
                f"Examples: {', '.join(p.get('reason', 'N/A') for p in zoom_points[:3])}\n"
                f"Output: {zoomed_path}"
            )
        except Exception as exc:
            return f"ERROR applying magic zoom: {exc}\n{traceback.format_exc()}"

    # ------------------------------------------------------------------
    # 10. Silence removal
    # ------------------------------------------------------------------

    def remove_silence(self, mode: str = "normal") -> str:
        """Remove dead air and filler words."""
        try:
            from aividio.effects.silence_remover import SilenceRemover

            if self.ctx.final_video_path is None:
                return "ERROR: No video available."

            remover = SilenceRemover()

            if self.ctx.word_timestamps:
                trimmed_path, stats = remover.smart_trim(
                    video_path=self.ctx.final_video_path,
                    word_timestamps=self.ctx.word_timestamps,
                    mode=mode,
                    remove_fillers=True,
                )
            else:
                trimmed_path = remover.remove_silence(
                    video_path=self.ctx.final_video_path,
                    mode=mode,
                )
                stats = {}

            self.ctx.final_video_path = trimmed_path

            return (
                f"Silence removal complete.\n"
                f"Mode: {mode}\n"
                f"Output: {trimmed_path}\n"
                f"Stats: {json.dumps(stats, default=str) if stats else 'N/A'}"
            )
        except Exception as exc:
            return f"ERROR removing silence: {exc}\n{traceback.format_exc()}"

    # ------------------------------------------------------------------
    # 11. B-roll insertion
    # ------------------------------------------------------------------

    def add_broll(self, max_clips: int = 6) -> str:
        """Insert contextual B-roll footage."""
        try:
            from aividio.effects.magic_broll import MagicBRoll

            if self.ctx.final_video_path is None:
                return "ERROR: No video available."
            if not self.ctx.word_timestamps:
                return "ERROR: No word timestamps for B-roll analysis."

            broll_engine = MagicBRoll(settings=self.settings)

            # Analyse transcript for B-roll moments
            suggestions = broll_engine.analyze_transcript(
                word_timestamps=self.ctx.word_timestamps,
                script=self.ctx.script,
                max_clips=max_clips,
            )

            if not suggestions:
                return "No B-roll opportunities identified. Skipping."

            # Source B-roll clips from stock providers
            from aividio.services.media import create_media_provider

            media_provider = create_media_provider(settings=self.settings)
            broll_dir = self.ctx.work_dir / "broll"
            broll_dir.mkdir(parents=True, exist_ok=True)

            broll_clips: list[dict] = []
            for i, suggestion in enumerate(suggestions):
                try:
                    result = media_provider.search_and_download(
                        query=suggestion["visual_query"],
                        media_type="video",
                        output_dir=broll_dir,
                        section_index=i,
                    )
                    broll_clips.append({
                        "start": suggestion["start"],
                        "end": suggestion["end"],
                        "clip_path": str(result["path"]),
                    })
                except Exception as exc:
                    logger.warning("Failed to source B-roll for %r: %s", suggestion["visual_query"], exc)

            if not broll_clips:
                return "Could not source any B-roll clips. Skipping."

            output_path = self.ctx.work_dir / "final_broll.mp4"
            result_path = broll_engine.insert_broll(
                video_path=self.ctx.final_video_path,
                broll_clips=broll_clips,
                output_path=output_path,
            )

            self.ctx.final_video_path = result_path

            self._track("claude", "broll_analysis", input_tokens=1000, output_tokens=500)

            return (
                f"B-roll inserted successfully.\n"
                f"Clips inserted: {len(broll_clips)}/{len(suggestions)} suggested\n"
                f"Output: {result_path}"
            )
        except Exception as exc:
            return f"ERROR adding B-roll: {exc}\n{traceback.format_exc()}"

    # ------------------------------------------------------------------
    # 12. Emoji & SFX
    # ------------------------------------------------------------------

    def add_emoji_sfx(self) -> str:
        """Add emoji overlays and sound effects."""
        try:
            from aividio.effects.emoji_sfx import EmojiSFXEngine

            if self.ctx.final_video_path is None:
                return "ERROR: No video available."
            if not self.ctx.word_timestamps:
                return "ERROR: No word timestamps."

            engine = EmojiSFXEngine(settings=self.settings)
            output_path = self.ctx.work_dir / "final_emoji_sfx.mp4"

            enhanced_path = engine.auto_enhance(
                video_path=self.ctx.final_video_path,
                word_timestamps=self.ctx.word_timestamps,
                output_path=output_path,
            )

            self.ctx.final_video_path = enhanced_path

            return (
                f"Emoji and SFX effects applied.\n"
                f"Output: {enhanced_path}"
            )
        except Exception as exc:
            return f"ERROR adding emoji/SFX: {exc}\n{traceback.format_exc()}"

    # ------------------------------------------------------------------
    # 13. Thumbnail
    # ------------------------------------------------------------------

    def generate_thumbnail(self, style: str = "auto") -> str:
        """Generate video thumbnail."""
        try:
            from aividio.services.imagegen import create_image_generator

            if self.ctx.script is None:
                return "ERROR: No script available."

            generator = create_image_generator(settings=self.settings)

            title = self.ctx.script.get("title", self.ctx.topic)
            thumbnail_config = self.profile.thumbnail
            thumb_style = thumbnail_config.style if style == "auto" else style

            self.ctx.thumbnail_path = Path(generator.generate(
                prompt=f"YouTube thumbnail for: {title}. Style: {thumb_style}",
                output_path=self.ctx.work_dir / "thumbnail.png",
            ))

            self._track("dalle3", "thumbnail_generation", images=1)

            return (
                f"Thumbnail generated.\n"
                f"Style: {thumb_style}\n"
                f"Output: {self.ctx.thumbnail_path}"
            )
        except Exception as exc:
            return f"ERROR generating thumbnail: {exc}\n{traceback.format_exc()}"

    # ------------------------------------------------------------------
    # 14. SEO optimisation
    # ------------------------------------------------------------------

    def optimize_seo(self) -> str:
        """Optimise title, description, tags for YouTube SEO."""
        try:
            from aividio.seo.optimizer import SEOOptimizer

            if self.ctx.script is None:
                return "ERROR: No script available."

            optimizer = SEOOptimizer(settings=self.settings)

            # Optimise title
            title_options = optimizer.optimize_title(
                title=self.ctx.script.get("title", ""),
                topic=self.ctx.topic,
                niche=self.profile.niche,
            )
            best_title = title_options[0] if title_options else {}

            # Generate optimised description
            description = optimizer.optimize_description(
                script=self.ctx.script,
                channel=self.profile,
            )

            # Generate tags
            tags = optimizer.generate_tags(script=self.ctx.script)

            # Update script with optimised metadata
            if best_title:
                self.ctx.script["title"] = best_title.get("title", self.ctx.script.get("title", ""))
            self.ctx.script["description"] = description
            self.ctx.script["tags"] = tags

            self._track("claude", "seo_optimization", input_tokens=3000, output_tokens=3000)

            return (
                f"SEO optimisation complete.\n"
                f"Optimised title: {self.ctx.script['title']}\n"
                f"CTR score: {best_title.get('estimated_ctr_score', 'N/A')}\n"
                f"Tags: {len(tags)}\n"
                f"Description length: {len(description)} chars"
            )
        except Exception as exc:
            return f"ERROR optimising SEO: {exc}\n{traceback.format_exc()}"

    # ------------------------------------------------------------------
    # 15. Brand kit
    # ------------------------------------------------------------------

    def apply_brand_kit(self) -> str:
        """Apply branding (logo, watermark, intro/outro)."""
        try:
            from aividio.brand import add_logo_overlay

            if self.ctx.final_video_path is None:
                return "ERROR: No video available."

            # Check if brand kit exists for this profile
            brand_kit_path = self.settings.profiles_dir / self.profile.name / "brand_kit.yaml"
            if not brand_kit_path.exists():
                return (
                    f"No brand kit found at {brand_kit_path}. "
                    "Skipping brand application. You can create a brand kit YAML for this channel."
                )

            # Load brand kit and apply
            import yaml

            with open(brand_kit_path) as f:
                kit_data = yaml.safe_load(f)

            # Apply logo if configured
            logo_path = kit_data.get("logo_path")
            if logo_path and Path(logo_path).exists():
                output_path = self.ctx.work_dir / "final_branded.mp4"
                branded_path = add_logo_overlay(
                    video_path=self.ctx.final_video_path,
                    logo_path=Path(logo_path),
                    output_path=output_path,
                )
                self.ctx.final_video_path = branded_path
                return f"Brand kit applied. Logo added. Output: {branded_path}"

            return "Brand kit loaded but no logo/watermark configured."
        except Exception as exc:
            return f"ERROR applying brand kit: {exc}\n{traceback.format_exc()}"

    # ------------------------------------------------------------------
    # 16. Platform export
    # ------------------------------------------------------------------

    def export_platforms(self, platforms: list[str] | None = None) -> str:
        """Export for multiple platforms."""
        try:
            from aividio.platforms.exporter import MultiPlatformExporter

            if self.ctx.final_video_path is None:
                return "ERROR: No video available."

            platforms = platforms or ["youtube"]
            exporter = MultiPlatformExporter()

            results = exporter.export(
                video_path=self.ctx.final_video_path,
                platforms=platforms,
                profile=self.profile,
            )

            output_summary = "\n".join(
                f"  {platform}: {path}" for platform, path in results.items()
            )

            return (
                f"Exported for {len(results)} platform(s).\n"
                f"{output_summary}"
            )
        except Exception as exc:
            return f"ERROR exporting for platforms: {exc}\n{traceback.format_exc()}"

    # ------------------------------------------------------------------
    # 17. Viral clip extraction
    # ------------------------------------------------------------------

    def extract_clips(
        self,
        count: int = 3,
        format: str = "portrait",
    ) -> str:
        """Extract viral short-form clips from the video."""
        try:
            from aividio.effects.magic_clips import MagicClips

            if self.ctx.final_video_path is None:
                return "ERROR: No video available."
            if not self.ctx.word_timestamps:
                return "ERROR: No word timestamps."

            clips_engine = MagicClips(settings=self.settings)

            # Analyse for clip-worthy segments
            clip_suggestions = clips_engine.analyze_for_clips(
                word_timestamps=self.ctx.word_timestamps,
                script=self.ctx.script,
                count=count,
            )

            if not clip_suggestions:
                return "No viral-worthy clips identified."

            # Extract each clip
            clips_dir = self.ctx.work_dir / "clips"
            clips_dir.mkdir(parents=True, exist_ok=True)

            extracted: list[str] = []
            for i, clip in enumerate(clip_suggestions):
                output_path = clips_dir / f"clip_{i + 1:02d}.mp4"
                clip_path = clips_engine.extract_clip(
                    video_path=self.ctx.final_video_path,
                    start=clip["start"],
                    end=clip["end"],
                    output_path=output_path,
                    reformat=format if format != "landscape" else None,
                )
                extracted.append(
                    f"  Clip {i + 1}: {clip.get('title', 'N/A')} "
                    f"(score={clip.get('score', 'N/A')}, {clip['end'] - clip['start']:.0f}s) -> {clip_path}"
                )

            self._track("claude", "clip_analysis", input_tokens=1000, output_tokens=500)

            return (
                f"Extracted {len(extracted)} viral clips.\n"
                + "\n".join(extracted)
            )
        except Exception as exc:
            return f"ERROR extracting clips: {exc}\n{traceback.format_exc()}"

    # ------------------------------------------------------------------
    # 18. YouTube upload
    # ------------------------------------------------------------------

    def upload_youtube(self, visibility: str = "private") -> str:
        """Upload to YouTube."""
        try:
            from aividio.services.youtube.auth import get_credentials
            from aividio.services.youtube.uploader import YouTubeUploader

            if self.ctx.final_video_path is None:
                return "ERROR: No video available."
            if self.ctx.script is None:
                return "ERROR: No script for metadata."

            token_path = self.settings.data_dir / "youtube_token.json"
            client_secret_path = self.settings.data_dir / "client_secret.json"

            if not client_secret_path.exists():
                return (
                    f"ERROR: YouTube client_secret.json not found at {client_secret_path}. "
                    "Set up YouTube API credentials first."
                )

            credentials = get_credentials(
                token_path=token_path,
                client_secret_path=client_secret_path,
            )

            uploader = YouTubeUploader(credentials=credentials)
            yt_config = self.profile.youtube

            video_id = uploader.upload(
                video_path=self.ctx.final_video_path,
                title=self.ctx.script.get("title", self.ctx.topic),
                description=self.ctx.script.get("description", ""),
                tags=self.ctx.script.get("tags", []),
                category_id=yt_config.category_id,
                visibility=visibility,
                thumbnail_path=self.ctx.thumbnail_path,
            )

            self._track("youtube_upload", "upload")

            return (
                f"Video uploaded to YouTube.\n"
                f"YouTube Video ID: {video_id}\n"
                f"URL: https://youtu.be/{video_id}\n"
                f"Visibility: {visibility}"
            )
        except Exception as exc:
            return f"ERROR uploading to YouTube: {exc}\n{traceback.format_exc()}"

    # ------------------------------------------------------------------
    # 19. Cost estimation
    # ------------------------------------------------------------------

    def estimate_cost(self, steps: list[str] | None = None) -> str:
        """Estimate cost for planned steps."""
        try:
            estimate = self.tracker.estimate_video_cost(
                profile_name=self.profile.name,
                duration_minutes=10.0,
                llm_provider="claude",
                tts_provider=self.profile.voice.provider,
                image_provider=self.settings.default_image_provider,
                num_images=len(self.ctx.script.get("sections", [])) if self.ctx.script else 15,
            )

            breakdown_str = "\n".join(
                f"  {key}: ${value:.4f}"
                for key, value in estimate["breakdown"].items()
            )

            return (
                f"Cost estimate for video production:\n"
                f"{breakdown_str}\n"
                f"Total estimated cost: ${estimate['total_usd']:.4f}\n"
                f"Current spend so far: ${self._total_cost:.4f}"
            )
        except Exception as exc:
            return f"ERROR estimating cost: {exc}\n{traceback.format_exc()}"

    # ------------------------------------------------------------------
    # 20. Usage tracking
    # ------------------------------------------------------------------

    def track_usage(self, service: str, operation: str, cost: float) -> str:
        """Log a manual usage event."""
        try:
            self.tracker.track(
                service=service,
                operation=operation,
                cost_usd=cost,
                video_id=self.ctx.video_id,
            )
            self._total_cost += cost
            return f"Usage tracked: {service}/{operation} ${cost:.4f}"
        except Exception as exc:
            return f"ERROR tracking usage: {exc}\n{traceback.format_exc()}"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _track(
        self,
        service: str,
        operation: str,
        **kwargs: Any,
    ) -> None:
        """Track usage and accumulate cost."""
        try:
            event = self.tracker.track(
                service=service,
                operation=operation,
                video_id=self.ctx.video_id,
                **kwargs,
            )
            self._total_cost += event.cost_usd
        except Exception:
            logger.warning("Failed to track usage for %s/%s", service, operation, exc_info=True)

    def execute(self, tool_name: str, tool_input: dict) -> str:
        """Route a tool call to the appropriate method.

        Args:
            tool_name: Name of the tool to call.
            tool_input: Dict of parameters for the tool.

        Returns:
            String result describing what happened.
        """
        tool_map: dict[str, Any] = {
            "generate_script": self.generate_script,
            "generate_voiceover": self.generate_voiceover,
            "transcribe_audio": self.transcribe_audio,
            "search_stock_media": self.search_stock_media,
            "generate_ai_video": self.generate_ai_video,
            "generate_ai_image": self.generate_ai_image,
            "assemble_video": self.assemble_video,
            "apply_captions": self.apply_captions,
            "apply_magic_zoom": self.apply_magic_zoom,
            "remove_silence": self.remove_silence,
            "add_broll": self.add_broll,
            "add_emoji_sfx": self.add_emoji_sfx,
            "generate_thumbnail": self.generate_thumbnail,
            "optimize_seo": self.optimize_seo,
            "apply_brand_kit": self.apply_brand_kit,
            "export_platforms": self.export_platforms,
            "extract_clips": self.extract_clips,
            "upload_youtube": self.upload_youtube,
            "estimate_cost": self.estimate_cost,
            "track_usage": self.track_usage,
        }

        handler = tool_map.get(tool_name)
        if handler is None:
            return f"ERROR: Unknown tool '{tool_name}'. Available: {sorted(tool_map.keys())}"

        # Filter tool_input to only include params the handler accepts
        import inspect

        sig = inspect.signature(handler)
        valid_params = set(sig.parameters.keys())
        filtered_input = {k: v for k, v in tool_input.items() if k in valid_params}

        return handler(**filtered_input)
