"""Complete tool registry for the AI Agent.

Maps every VIDMATION capability to a Claude tool_use compatible definition.
Each tool has: name, description, input_schema (JSON Schema), and an executor function.

Categories:
- Script Generation (5 tools)
- Text-to-Speech (6 tools)
- Media Sourcing (5 tools)
- Image Generation (4 tools)
- Video Generation (5 tools)
- Video Assembly (6 tools)
- Captions & Subtitles (5 tools)
- Effects & Post-Processing (8 tools)
- SEO & Content (8 tools)
- Brand & Templates (5 tools)
- Platform Export (5 tools)
- YouTube (4 tools)
- Analytics & Tracking (5 tools)
- Database Operations (6 tools)
- Notifications & Scheduling (4 tools)
- File & System (4 tools)
"""

from __future__ import annotations

import json
import logging
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from vidmation.config.profiles import ChannelProfile
    from vidmation.config.settings import Settings

logger = logging.getLogger("vidmation.agent.registry")


# ---------------------------------------------------------------------------
# ToolDefinition dataclass
# ---------------------------------------------------------------------------


@dataclass
class ToolDefinition:
    """A single tool available to the AI agent."""

    name: str
    description: str
    category: str
    input_schema: dict  # JSON Schema
    executor: Callable[..., str]  # Returns string result for Claude
    cost_estimate: float | None = None  # Estimated USD cost per call
    requires_api_key: str | None = None  # Which API key is needed


# ---------------------------------------------------------------------------
# ToolRegistry
# ---------------------------------------------------------------------------


class ToolRegistry:
    """Central registry of all tools available to the AI agent.

    On initialisation, every service in the VIDMATION codebase is registered
    as a callable tool with a JSON-Schema input definition and an executor
    function that catches exceptions and returns a string result suitable for
    Claude's ``tool_result`` content block.
    """

    def __init__(
        self,
        settings: "Settings",
        profile: "ChannelProfile",
        ctx: dict[str, Any] | None = None,
    ) -> None:
        self.settings = settings
        self.profile = profile
        self.ctx: dict[str, Any] = ctx or {}
        self._tools: dict[str, ToolDefinition] = {}
        self._register_all()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_tool(self, name: str) -> ToolDefinition:
        """Return a tool by name, or raise ``KeyError``."""
        if name not in self._tools:
            raise KeyError(
                f"Unknown tool {name!r}. Available: {sorted(self._tools)}"
            )
        return self._tools[name]

    def list_tools(self) -> list[ToolDefinition]:
        """Return all registered tools."""
        return list(self._tools.values())

    def list_by_category(self, category: str) -> list[ToolDefinition]:
        """Return tools in a specific category."""
        return [t for t in self._tools.values() if t.category == category]

    def get_claude_tools(self) -> list[dict]:
        """Return tool definitions formatted for the Claude API ``tools`` param.

        Each entry is a dict with ``name``, ``description``, and
        ``input_schema`` -- ready to pass directly to
        ``anthropic.messages.create(tools=...)``.
        """
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in self._tools.values()
        ]

    def execute(self, name: str, **kwargs: Any) -> str:
        """Execute a tool by name.  Returns a JSON string on success or
        an error description on failure.  Never raises.
        """
        try:
            tool = self.get_tool(name)
            result = tool.executor(**kwargs)
            return result
        except Exception as exc:
            tb = traceback.format_exc()
            logger.error("Tool %r failed: %s\n%s", name, exc, tb)
            return json.dumps(
                {"error": str(exc), "tool": name, "traceback": tb}
            )

    @property
    def tool_count(self) -> int:
        return len(self._tools)

    # ------------------------------------------------------------------
    # Registration helpers
    # ------------------------------------------------------------------

    def _register(self, tool: ToolDefinition) -> None:
        """Add a tool to the registry."""
        if tool.name in self._tools:
            logger.warning("Overwriting tool %r", tool.name)
        self._tools[tool.name] = tool
        logger.debug("Registered tool: %s [%s]", tool.name, tool.category)

    def _safe_exec(self, fn: Callable[..., Any]) -> Callable[..., str]:
        """Wrap *fn* so it always returns a JSON string and never raises."""

        def wrapper(**kwargs: Any) -> str:
            try:
                result = fn(**kwargs)
                # Convert Path objects to strings for JSON serialisation
                if isinstance(result, Path):
                    return json.dumps({"path": str(result)})
                if isinstance(result, (dict, list)):
                    return json.dumps(result, default=str)
                if isinstance(result, tuple):
                    return json.dumps(
                        {"result": [str(r) if isinstance(r, Path) else r for r in result]},
                        default=str,
                    )
                return json.dumps({"result": str(result)}, default=str)
            except Exception as exc:
                return json.dumps({"error": str(exc)})

        return wrapper

    # ------------------------------------------------------------------
    # Master registration dispatcher
    # ------------------------------------------------------------------

    def _register_all(self) -> None:
        """Register every tool category."""
        self._register_script_tools()
        self._register_tts_tools()
        self._register_media_tools()
        self._register_imagegen_tools()
        self._register_videogen_tools()
        self._register_assembly_tools()
        self._register_caption_tools()
        self._register_effects_tools()
        self._register_seo_tools()
        self._register_brand_tools()
        self._register_platform_tools()
        self._register_youtube_tools()
        self._register_analytics_tools()
        self._register_db_tools()
        self._register_notification_tools()
        self._register_file_tools()
        logger.info(
            "Tool registry initialised: %d tools across %d categories",
            self.tool_count,
            len({t.category for t in self._tools.values()}),
        )

    # ===================================================================
    # SCRIPT GENERATION (5 tools)
    # ===================================================================

    def _register_script_tools(self) -> None:
        # -- generate_script -----------------------------------------------
        def _generate_script(
            topic: str,
            provider: str = "claude",
            **kwargs: Any,
        ) -> str:
            from vidmation.services.scriptgen import create_script_generator

            gen = create_script_generator(
                provider=provider, settings=self.settings
            )
            script = gen.generate(topic=topic, profile=self.profile)
            return json.dumps(script, default=str)

        self._register(
            ToolDefinition(
                name="generate_script",
                description=(
                    "Generate a structured video script with sections, visual queries, "
                    "narration, and timing estimates. Returns JSON with title, hook, "
                    "sections[], outro, tags, and total_estimated_duration_seconds."
                ),
                category="script",
                input_schema={
                    "type": "object",
                    "required": ["topic"],
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "The video topic or title idea.",
                        },
                        "provider": {
                            "type": "string",
                            "enum": ["claude", "openai"],
                            "description": "LLM provider for script generation.",
                            "default": "claude",
                        },
                    },
                },
                executor=_generate_script,
                cost_estimate=0.02,
                requires_api_key="anthropic_api_key",
            )
        )

        # -- optimize_retention --------------------------------------------
        def _optimize_retention(script: str, **kwargs: Any) -> str:
            from vidmation.services.scriptgen.retention import RetentionOptimizer

            optimizer = RetentionOptimizer(settings=self.settings)
            script_dict = json.loads(script)
            optimized = optimizer.optimize(script_dict, profile=self.profile)
            return json.dumps(optimized, default=str)

        self._register(
            ToolDefinition(
                name="optimize_retention",
                description=(
                    "Optimize a video script for viewer retention. Analyzes hook strength, "
                    "pacing, curiosity gaps, emotional variety, and CTA placement, then "
                    "rewrites weak sections. Pass the script as a JSON string."
                ),
                category="script",
                input_schema={
                    "type": "object",
                    "required": ["script"],
                    "properties": {
                        "script": {
                            "type": "string",
                            "description": "The video script as a JSON string.",
                        },
                    },
                },
                executor=_optimize_retention,
                cost_estimate=0.04,
                requires_api_key="anthropic_api_key",
            )
        )

        # -- generate_hooks ------------------------------------------------
        def _generate_hooks(topic: str, count: int = 5, **kwargs: Any) -> str:
            from vidmation.services.scriptgen.retention import RetentionOptimizer

            optimizer = RetentionOptimizer(settings=self.settings)
            hooks = optimizer.generate_hooks(topic=topic, count=count)
            return json.dumps(hooks, default=str)

        self._register(
            ToolDefinition(
                name="generate_hooks",
                description=(
                    "Generate multiple hook variations for A/B testing. Each hook grabs "
                    "attention in the first 5 seconds using different styles (question, "
                    "bold_claim, statistic, story_tease, controversy, etc.)."
                ),
                category="script",
                input_schema={
                    "type": "object",
                    "required": ["topic"],
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "The video topic.",
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of hook variations to generate.",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 20,
                        },
                    },
                },
                executor=_generate_hooks,
                cost_estimate=0.01,
                requires_api_key="anthropic_api_key",
            )
        )

        # -- generate_titles -----------------------------------------------
        def _generate_titles(script: str, count: int = 10, **kwargs: Any) -> str:
            from vidmation.services.scriptgen.retention import RetentionOptimizer

            optimizer = RetentionOptimizer(settings=self.settings)
            script_dict = json.loads(script)
            titles = optimizer.generate_titles(script_dict, count=count)
            return json.dumps(titles, default=str)

        self._register(
            ToolDefinition(
                name="generate_titles",
                description=(
                    "Generate YouTube title variations optimized for click-through rate. "
                    "Returns titles with CTR predictions and style labels."
                ),
                category="script",
                input_schema={
                    "type": "object",
                    "required": ["script"],
                    "properties": {
                        "script": {
                            "type": "string",
                            "description": "The video script as a JSON string.",
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of title variations.",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 20,
                        },
                    },
                },
                executor=_generate_titles,
                cost_estimate=0.01,
                requires_api_key="anthropic_api_key",
            )
        )

        # -- generate_prompt_pack ------------------------------------------
        def _generate_prompt_pack(
            topic: str, script: str, **kwargs: Any
        ) -> str:
            from vidmation.services.scriptgen.prompt_packs import (
                PromptPackGenerator,
            )

            gen = PromptPackGenerator(settings=self.settings)
            script_dict = json.loads(script)
            pack = gen.generate(
                topic=topic, channel=self.profile, script=script_dict
            )
            return json.dumps(pack, default=str)

        self._register(
            ToolDefinition(
                name="generate_prompt_pack",
                description=(
                    "Generate a comprehensive prompt pack for the entire video production "
                    "pipeline. Includes channel positioning, video brief, generation rules, "
                    "per-section visual prompts, and SEO payloads for YouTube/TikTok/Instagram."
                ),
                category="script",
                input_schema={
                    "type": "object",
                    "required": ["topic", "script"],
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "The video topic.",
                        },
                        "script": {
                            "type": "string",
                            "description": "The video script as a JSON string.",
                        },
                    },
                },
                executor=_generate_prompt_pack,
                cost_estimate=0.03,
                requires_api_key="anthropic_api_key",
            )
        )

    # ===================================================================
    # TEXT-TO-SPEECH (6 tools)
    # ===================================================================

    def _register_tts_tools(self) -> None:
        # -- synthesize_speech ---------------------------------------------
        def _synthesize_speech(
            text: str,
            provider: str = "elevenlabs",
            voice_id: str = "",
            output_path: str = "",
            speed: float = 1.0,
            **kwargs: Any,
        ) -> str:
            from vidmation.config.profiles import VoiceConfig
            from vidmation.services.tts import create_tts_provider

            tts = create_tts_provider(provider=provider, settings=self.settings)
            vc = VoiceConfig(
                provider=provider,
                voice_id=voice_id or self.profile.voice.voice_id,
                stability=self.profile.voice.stability,
                similarity_boost=self.profile.voice.similarity_boost,
                speed=speed,
            )
            out = Path(output_path) if output_path else Path(f"/tmp/vidmation_tts_{hash(text[:50])}.mp3")
            path, duration = tts.synthesize(text=text, voice_config=vc, output_path=out)
            return json.dumps({"path": str(path), "duration_seconds": duration})

        self._register(
            ToolDefinition(
                name="synthesize_speech",
                description=(
                    "Convert text to speech audio using ElevenLabs, OpenAI, Replicate, "
                    "or fal.ai TTS. Returns the audio file path and duration in seconds."
                ),
                category="tts",
                input_schema={
                    "type": "object",
                    "required": ["text"],
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The narration text to speak.",
                        },
                        "provider": {
                            "type": "string",
                            "enum": ["elevenlabs", "openai", "replicate", "fal"],
                            "description": "TTS provider to use.",
                            "default": "elevenlabs",
                        },
                        "voice_id": {
                            "type": "string",
                            "description": "Voice ID or name. Provider-specific.",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Where to save the audio file.",
                        },
                        "speed": {
                            "type": "number",
                            "description": "Speech speed multiplier (1.0 = normal).",
                            "default": 1.0,
                            "minimum": 0.5,
                            "maximum": 2.0,
                        },
                    },
                },
                executor=_synthesize_speech,
                cost_estimate=0.01,
                requires_api_key="elevenlabs_api_key",
            )
        )

        # -- list_voices ---------------------------------------------------
        def _list_voices(provider: str = "elevenlabs", **kwargs: Any) -> str:
            from vidmation.services.tts import create_tts_provider

            tts = create_tts_provider(provider=provider, settings=self.settings)
            voices = tts.list_voices()
            return json.dumps(voices, default=str)

        self._register(
            ToolDefinition(
                name="list_voices",
                description="List all available voices for a TTS provider.",
                category="tts",
                input_schema={
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": ["elevenlabs", "openai", "replicate", "fal"],
                            "description": "TTS provider.",
                            "default": "elevenlabs",
                        },
                    },
                },
                executor=_list_voices,
                cost_estimate=0.0,
            )
        )

        # -- clone_voice ---------------------------------------------------
        def _clone_voice(
            audio_samples: list[str],
            name: str,
            description: str = "",
            provider: str = "elevenlabs",
            **kwargs: Any,
        ) -> str:
            from vidmation.services.tts.voice_cloning import VoiceCloner

            cloner = VoiceCloner(settings=self.settings)
            result = cloner.clone_voice(
                audio_samples=[Path(p) for p in audio_samples],
                name=name,
                description=description,
                provider=provider,
            )
            return json.dumps(result, default=str)

        self._register(
            ToolDefinition(
                name="clone_voice",
                description=(
                    "Clone a voice from one or more audio samples. Returns the cloned "
                    "voice ID that can be used for synthesize_speech calls."
                ),
                category="tts",
                input_schema={
                    "type": "object",
                    "required": ["audio_samples", "name"],
                    "properties": {
                        "audio_samples": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Paths to audio sample files (WAV/MP3, 10-30 seconds each).",
                            "minItems": 1,
                        },
                        "name": {
                            "type": "string",
                            "description": "Human-readable name for the cloned voice.",
                        },
                        "description": {
                            "type": "string",
                            "description": "Optional description of the voice.",
                        },
                        "provider": {
                            "type": "string",
                            "enum": ["elevenlabs", "replicate"],
                            "description": "Voice cloning backend.",
                            "default": "elevenlabs",
                        },
                    },
                },
                executor=_clone_voice,
                cost_estimate=0.0,
                requires_api_key="elevenlabs_api_key",
            )
        )

        # -- preview_voice -------------------------------------------------
        def _preview_voice(
            voice_id: str,
            text: str = "",
            provider: str = "elevenlabs",
            **kwargs: Any,
        ) -> str:
            from vidmation.services.tts.voice_cloning import VoiceCloner

            cloner = VoiceCloner(settings=self.settings)
            path = cloner.preview_voice(
                voice_id=voice_id, text=text or None, provider=provider
            )
            return json.dumps({"path": str(path)})

        self._register(
            ToolDefinition(
                name="preview_voice",
                description="Generate a short audio preview using a voice ID.",
                category="tts",
                input_schema={
                    "type": "object",
                    "required": ["voice_id"],
                    "properties": {
                        "voice_id": {
                            "type": "string",
                            "description": "The voice ID to preview.",
                        },
                        "text": {
                            "type": "string",
                            "description": "Custom preview text (default: standard greeting).",
                        },
                        "provider": {
                            "type": "string",
                            "enum": ["elevenlabs", "replicate"],
                            "default": "elevenlabs",
                        },
                    },
                },
                executor=_preview_voice,
                cost_estimate=0.005,
            )
        )

        # -- synthesize_section --------------------------------------------
        def _synthesize_section(
            section_index: int,
            sections: str,
            provider: str = "elevenlabs",
            output_dir: str = "",
            **kwargs: Any,
        ) -> str:
            from vidmation.config.profiles import VoiceConfig
            from vidmation.services.tts import create_tts_provider

            sections_list = json.loads(sections)
            if section_index < 0 or section_index >= len(sections_list):
                return json.dumps({"error": f"Section index {section_index} out of range"})

            section = sections_list[section_index]
            text = section.get("narration", section.get("text", ""))

            tts = create_tts_provider(provider=provider, settings=self.settings)
            vc = VoiceConfig(
                provider=provider,
                voice_id=self.profile.voice.voice_id,
                stability=self.profile.voice.stability,
                similarity_boost=self.profile.voice.similarity_boost,
                speed=self.profile.voice.speed,
            )
            out_dir = Path(output_dir) if output_dir else Path("/tmp/vidmation_sections")
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"section_{section_index:03d}.mp3"

            path, duration = tts.synthesize(text=text, voice_config=vc, output_path=out_path)
            return json.dumps({
                "path": str(path),
                "duration_seconds": duration,
                "section_index": section_index,
            })

        self._register(
            ToolDefinition(
                name="synthesize_section",
                description=(
                    "Synthesize audio for a single script section by index. "
                    "Useful for parallel section-by-section TTS generation."
                ),
                category="tts",
                input_schema={
                    "type": "object",
                    "required": ["section_index", "sections"],
                    "properties": {
                        "section_index": {
                            "type": "integer",
                            "description": "Zero-based index of the section to synthesize.",
                            "minimum": 0,
                        },
                        "sections": {
                            "type": "string",
                            "description": "JSON array of script sections.",
                        },
                        "provider": {
                            "type": "string",
                            "enum": ["elevenlabs", "openai", "replicate", "fal"],
                            "default": "elevenlabs",
                        },
                        "output_dir": {
                            "type": "string",
                            "description": "Directory for output audio files.",
                        },
                    },
                },
                executor=_synthesize_section,
                cost_estimate=0.005,
            )
        )

        # -- concatenate_audio ---------------------------------------------
        def _concatenate_audio(
            audio_paths: list[str], output_path: str = "", **kwargs: Any
        ) -> str:
            import ffmpeg as _ffmpeg

            paths = [Path(p) for p in audio_paths]
            for p in paths:
                if not p.exists():
                    return json.dumps({"error": f"Audio file not found: {p}"})

            out = Path(output_path) if output_path else Path("/tmp/vidmation_concat.mp3")
            out.parent.mkdir(parents=True, exist_ok=True)

            # Build concat list
            concat_list = out.with_suffix(".txt")
            concat_list.write_text(
                "\n".join(f"file '{p}'" for p in paths), encoding="utf-8"
            )

            try:
                (
                    _ffmpeg.input(str(concat_list), format="concat", safe=0)
                    .output(str(out), acodec="aac", audio_bitrate="192k")
                    .overwrite_output()
                    .run(quiet=True)
                )
            except _ffmpeg.Error as exc:
                stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
                return json.dumps({"error": f"Concatenation failed: {stderr}"})

            from vidmation.utils.ffmpeg import get_duration

            duration = get_duration(out)
            return json.dumps({"path": str(out), "duration_seconds": duration})

        self._register(
            ToolDefinition(
                name="concatenate_audio",
                description="Concatenate multiple audio files into a single combined file.",
                category="tts",
                input_schema={
                    "type": "object",
                    "required": ["audio_paths"],
                    "properties": {
                        "audio_paths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Ordered list of audio file paths to concatenate.",
                            "minItems": 1,
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Output file path for the concatenated audio.",
                        },
                    },
                },
                executor=_concatenate_audio,
                cost_estimate=0.0,
            )
        )

    # ===================================================================
    # MEDIA SOURCING (5 tools)
    # ===================================================================

    def _register_media_tools(self) -> None:
        # -- search_stock_video --------------------------------------------
        def _search_stock_video(
            query: str, count: int = 5, provider: str = "pexels", **kwargs: Any
        ) -> str:
            from vidmation.services.media import create_media_provider

            media = create_media_provider(provider=provider, settings=self.settings)
            results = media.search_videos(query=query, count=count)
            return json.dumps(results, default=str)

        self._register(
            ToolDefinition(
                name="search_stock_video",
                description="Search for stock videos by keyword. Returns results with download URLs.",
                category="media",
                input_schema={
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {"type": "string", "description": "Search query for stock videos."},
                        "count": {"type": "integer", "default": 5, "minimum": 1, "maximum": 30, "description": "Number of results."},
                        "provider": {"type": "string", "enum": ["pexels", "pixabay"], "default": "pexels"},
                    },
                },
                executor=_search_stock_video,
                cost_estimate=0.0,
                requires_api_key="pexels_api_key",
            )
        )

        # -- search_stock_image --------------------------------------------
        def _search_stock_image(
            query: str, count: int = 5, provider: str = "pexels", **kwargs: Any
        ) -> str:
            from vidmation.services.media import create_media_provider

            media = create_media_provider(provider=provider, settings=self.settings)
            results = media.search_images(query=query, count=count)
            return json.dumps(results, default=str)

        self._register(
            ToolDefinition(
                name="search_stock_image",
                description="Search for stock images by keyword. Returns results with download URLs.",
                category="media",
                input_schema={
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {"type": "string", "description": "Search query for stock images."},
                        "count": {"type": "integer", "default": 5, "minimum": 1, "maximum": 30},
                        "provider": {"type": "string", "enum": ["pexels", "pixabay"], "default": "pexels"},
                    },
                },
                executor=_search_stock_image,
                cost_estimate=0.0,
                requires_api_key="pexels_api_key",
            )
        )

        # -- download_media ------------------------------------------------
        def _download_media(
            url: str, output_path: str, provider: str = "pexels", **kwargs: Any
        ) -> str:
            from vidmation.services.media import create_media_provider

            media = create_media_provider(provider=provider, settings=self.settings)
            result = media.download(url=url, output_path=Path(output_path))
            return json.dumps({"path": str(result)})

        self._register(
            ToolDefinition(
                name="download_media",
                description="Download a media file from a URL to a local path.",
                category="media",
                input_schema={
                    "type": "object",
                    "required": ["url", "output_path"],
                    "properties": {
                        "url": {"type": "string", "description": "Direct download URL."},
                        "output_path": {"type": "string", "description": "Local file path to save to."},
                        "provider": {"type": "string", "enum": ["pexels", "pixabay"], "default": "pexels"},
                    },
                },
                executor=_download_media,
                cost_estimate=0.0,
            )
        )

        # -- search_and_download -------------------------------------------
        def _search_and_download(
            query: str,
            media_type: str = "video",
            output_dir: str = "/tmp/vidmation_media",
            section_index: int = 0,
            provider: str = "pexels",
            **kwargs: Any,
        ) -> str:
            from vidmation.services.media import create_media_provider

            media = create_media_provider(provider=provider, settings=self.settings)
            result = media.search_and_download(
                query=query,
                media_type=media_type,
                output_dir=Path(output_dir),
                section_index=section_index,
            )
            result["path"] = str(result["path"])
            return json.dumps(result)

        self._register(
            ToolDefinition(
                name="search_and_download",
                description=(
                    "Search for media and download the best result in one step. "
                    "Combines search + download into a single call."
                ),
                category="media",
                input_schema={
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {"type": "string", "description": "Search query."},
                        "media_type": {"type": "string", "enum": ["video", "image"], "default": "video"},
                        "output_dir": {"type": "string", "description": "Directory to save the file."},
                        "section_index": {"type": "integer", "default": 0, "description": "Section number for file naming."},
                        "provider": {"type": "string", "enum": ["pexels", "pixabay"], "default": "pexels"},
                    },
                },
                executor=_search_and_download,
                cost_estimate=0.0,
                requires_api_key="pexels_api_key",
            )
        )

        # -- bulk_source_media ---------------------------------------------
        def _bulk_source_media(
            sections: str,
            output_dir: str = "/tmp/vidmation_media",
            provider: str = "pexels",
            **kwargs: Any,
        ) -> str:
            from vidmation.services.media import create_media_provider

            media = create_media_provider(provider=provider, settings=self.settings)
            sections_list = json.loads(sections)
            results = []
            for i, sec in enumerate(sections_list):
                query = sec.get("visual_query", sec.get("heading", ""))
                vtype = sec.get("visual_type", "stock_video")
                mtype = "image" if "image" in vtype else "video"
                try:
                    result = media.search_and_download(
                        query=query,
                        media_type=mtype,
                        output_dir=Path(output_dir),
                        section_index=i,
                    )
                    result["path"] = str(result["path"])
                    result["section_index"] = i
                    results.append(result)
                except Exception as exc:
                    results.append({"section_index": i, "error": str(exc)})
            return json.dumps(results)

        self._register(
            ToolDefinition(
                name="bulk_source_media",
                description=(
                    "Source media for all script sections at once. Searches and downloads "
                    "stock video/images for each section based on its visual_query."
                ),
                category="media",
                input_schema={
                    "type": "object",
                    "required": ["sections"],
                    "properties": {
                        "sections": {"type": "string", "description": "JSON array of script sections."},
                        "output_dir": {"type": "string", "description": "Directory for downloaded files."},
                        "provider": {"type": "string", "enum": ["pexels", "pixabay"], "default": "pexels"},
                    },
                },
                executor=_bulk_source_media,
                cost_estimate=0.0,
                requires_api_key="pexels_api_key",
            )
        )

    # ===================================================================
    # IMAGE GENERATION (4 tools)
    # ===================================================================

    def _register_imagegen_tools(self) -> None:
        # -- generate_image_dalle ------------------------------------------
        def _generate_image_dalle(
            prompt: str, size: str = "1792x1024", output_path: str = "", **kwargs: Any
        ) -> str:
            from vidmation.services.imagegen.dalle import DalleImageGenerator

            gen = DalleImageGenerator(settings=self.settings)
            out = Path(output_path) if output_path else None
            path = gen.generate(prompt=prompt, size=size, output_path=out)
            return json.dumps({"path": str(path)})

        self._register(
            ToolDefinition(
                name="generate_image_dalle",
                description="Generate an image using OpenAI DALL-E 3. Best for photorealistic and artistic images.",
                category="imagegen",
                input_schema={
                    "type": "object",
                    "required": ["prompt"],
                    "properties": {
                        "prompt": {"type": "string", "description": "Detailed image description."},
                        "size": {"type": "string", "enum": ["1024x1024", "1792x1024", "1024x1792", "1280x720"], "default": "1792x1024"},
                        "output_path": {"type": "string", "description": "Optional output file path."},
                    },
                },
                executor=_generate_image_dalle,
                cost_estimate=0.08,
                requires_api_key="openai_api_key",
            )
        )

        # -- generate_image_replicate --------------------------------------
        def _generate_image_replicate(
            prompt: str,
            size: str = "1280x720",
            model: str = "black-forest-labs/flux-schnell",
            output_path: str = "",
            **kwargs: Any,
        ) -> str:
            from vidmation.services.imagegen.replicate_gen import ReplicateImageGenerator

            gen = ReplicateImageGenerator(settings=self.settings, model_id=model)
            out = Path(output_path) if output_path else None
            path = gen.generate(prompt=prompt, size=size, output_path=out)
            return json.dumps({"path": str(path)})

        self._register(
            ToolDefinition(
                name="generate_image_replicate",
                description="Generate an image via Replicate (Flux/SDXL). Fast and cost-effective.",
                category="imagegen",
                input_schema={
                    "type": "object",
                    "required": ["prompt"],
                    "properties": {
                        "prompt": {"type": "string", "description": "Image description."},
                        "size": {"type": "string", "default": "1280x720", "description": "WIDTHxHEIGHT."},
                        "model": {"type": "string", "default": "black-forest-labs/flux-schnell", "description": "Replicate model ID."},
                        "output_path": {"type": "string"},
                    },
                },
                executor=_generate_image_replicate,
                cost_estimate=0.003,
                requires_api_key="replicate_api_token",
            )
        )

        # -- generate_image_fal --------------------------------------------
        def _generate_image_fal(
            prompt: str,
            size: str = "1280x720",
            model: str = "fal-ai/flux/dev",
            output_path: str = "",
            **kwargs: Any,
        ) -> str:
            from vidmation.services.imagegen.fal_gen import FalImageGenerator

            gen = FalImageGenerator(settings=self.settings, model_id=model)
            out = Path(output_path) if output_path else None
            path = gen.generate(prompt=prompt, size=size, output_path=out)
            return json.dumps({"path": str(path)})

        self._register(
            ToolDefinition(
                name="generate_image_fal",
                description="Generate an image via fal.ai (Flux models). High quality with fast inference.",
                category="imagegen",
                input_schema={
                    "type": "object",
                    "required": ["prompt"],
                    "properties": {
                        "prompt": {"type": "string", "description": "Image description."},
                        "size": {"type": "string", "default": "1280x720"},
                        "model": {"type": "string", "default": "fal-ai/flux/dev"},
                        "output_path": {"type": "string"},
                    },
                },
                executor=_generate_image_fal,
                cost_estimate=0.0025,
                requires_api_key="fal_key",
            )
        )

        # -- generate_thumbnail --------------------------------------------
        def _generate_thumbnail(
            title: str,
            style: str = "cinematic",
            script: str = "",
            output_path: str = "",
            **kwargs: Any,
        ) -> str:
            from vidmation.services.scriptgen.retention import RetentionOptimizer

            optimizer = RetentionOptimizer(settings=self.settings)
            script_dict = json.loads(script) if script else {"title": title}
            concepts = optimizer.generate_thumbnail_concepts(script_dict, count=1)

            if not concepts:
                return json.dumps({"error": "No thumbnail concepts generated"})

            concept = concepts[0]
            prompt = concept.get("image_prompt", f"YouTube thumbnail for: {title}")

            from vidmation.services.imagegen import create_image_generator

            gen = create_image_generator(
                provider=self.settings.default_image_provider,
                settings=self.settings,
            )
            out = Path(output_path) if output_path else None
            path = gen.generate(prompt=prompt, size="1792x1024", output_path=out)
            return json.dumps({
                "path": str(path),
                "concept": concept,
            })

        self._register(
            ToolDefinition(
                name="generate_thumbnail",
                description=(
                    "Generate a YouTube thumbnail. Uses AI to create a concept with text "
                    "overlay ideas, then generates the image. Returns the image path and concept."
                ),
                category="imagegen",
                input_schema={
                    "type": "object",
                    "required": ["title"],
                    "properties": {
                        "title": {"type": "string", "description": "Video title for thumbnail concept."},
                        "style": {"type": "string", "default": "cinematic", "description": "Visual style hint."},
                        "script": {"type": "string", "description": "Optional script JSON for richer concepts."},
                        "output_path": {"type": "string"},
                    },
                },
                executor=_generate_thumbnail,
                cost_estimate=0.10,
                requires_api_key="anthropic_api_key",
            )
        )

    # ===================================================================
    # VIDEO GENERATION (5 tools)
    # ===================================================================

    def _register_videogen_tools(self) -> None:
        # -- generate_video_clip -------------------------------------------
        def _generate_video_clip(
            prompt: str,
            provider: str = "replicate",
            model: str = "",
            duration: float = 5.0,
            aspect_ratio: str = "16:9",
            output_path: str = "",
            **kwargs: Any,
        ) -> str:
            from vidmation.services.videogen import create_video_generator

            gen = create_video_generator(
                provider=provider,
                settings=self.settings,
                **({"model_id": model} if model else {}),
            )
            out = Path(output_path) if output_path else None
            path = gen.generate(prompt=prompt, duration=duration, aspect_ratio=aspect_ratio, output_path=out)
            return json.dumps({"path": str(path)})

        self._register(
            ToolDefinition(
                name="generate_video_clip",
                description=(
                    "Generate an AI video clip from a text prompt. Supports multiple "
                    "models: Kling, Runway Gen-3, MiniMax, Hunyuan, Wan AI via Replicate or fal.ai."
                ),
                category="videogen",
                input_schema={
                    "type": "object",
                    "required": ["prompt"],
                    "properties": {
                        "prompt": {"type": "string", "description": "Video scene description."},
                        "provider": {"type": "string", "enum": ["replicate", "fal", "local"], "default": "replicate"},
                        "model": {"type": "string", "description": "Specific model ID (optional)."},
                        "duration": {"type": "number", "default": 5.0, "minimum": 1.0, "maximum": 10.0},
                        "aspect_ratio": {"type": "string", "enum": ["16:9", "9:16", "1:1", "4:3"], "default": "16:9"},
                        "output_path": {"type": "string"},
                    },
                },
                executor=_generate_video_clip,
                cost_estimate=0.25,
                requires_api_key="replicate_api_token",
            )
        )

        # -- generate_video_from_image -------------------------------------
        def _generate_video_from_image(
            image_path: str,
            prompt: str,
            provider: str = "replicate",
            model: str = "",
            duration: float = 5.0,
            output_path: str = "",
            **kwargs: Any,
        ) -> str:
            from vidmation.services.videogen import create_video_generator

            gen = create_video_generator(
                provider=provider,
                settings=self.settings,
                **({"model_id": model} if model else {}),
            )
            out = Path(output_path) if output_path else None
            path = gen.generate_from_image(
                image_path=Path(image_path), prompt=prompt, duration=duration, output_path=out
            )
            return json.dumps({"path": str(path)})

        self._register(
            ToolDefinition(
                name="generate_video_from_image",
                description=(
                    "Generate a video clip from a reference image (image-to-video). "
                    "The image becomes the first frame and the model animates it."
                ),
                category="videogen",
                input_schema={
                    "type": "object",
                    "required": ["image_path", "prompt"],
                    "properties": {
                        "image_path": {"type": "string", "description": "Path to source image."},
                        "prompt": {"type": "string", "description": "Motion/animation description."},
                        "provider": {"type": "string", "enum": ["replicate", "fal"], "default": "replicate"},
                        "model": {"type": "string"},
                        "duration": {"type": "number", "default": 5.0, "minimum": 1.0, "maximum": 10.0},
                        "output_path": {"type": "string"},
                    },
                },
                executor=_generate_video_from_image,
                cost_estimate=0.30,
                requires_api_key="replicate_api_token",
            )
        )

        # -- generate_local_video ------------------------------------------
        def _generate_local_video(
            prompt: str,
            duration: float = 5.0,
            aspect_ratio: str = "16:9",
            output_path: str = "",
            **kwargs: Any,
        ) -> str:
            from vidmation.services.videogen.local_gen import LocalVideoGenerator

            gen = LocalVideoGenerator(settings=self.settings)
            out = Path(output_path) if output_path else None
            path = gen.generate(prompt=prompt, duration=duration, aspect_ratio=aspect_ratio, output_path=out)
            return json.dumps({"path": str(path)})

        self._register(
            ToolDefinition(
                name="generate_local_video",
                description=(
                    "Generate a procedural video clip locally using FFmpeg (free). "
                    "Supports text_card, gradient, particles, waveform, and ken_burns modes."
                ),
                category="videogen",
                input_schema={
                    "type": "object",
                    "required": ["prompt"],
                    "properties": {
                        "prompt": {"type": "string", "description": "Description (keywords like 'title card', 'gradient', 'particle' select the mode)."},
                        "duration": {"type": "number", "default": 5.0, "minimum": 1.0, "maximum": 60.0},
                        "aspect_ratio": {"type": "string", "enum": ["16:9", "9:16", "1:1", "4:3"], "default": "16:9"},
                        "output_path": {"type": "string"},
                    },
                },
                executor=_generate_local_video,
                cost_estimate=0.0,
            )
        )

        # -- generate_batch_clips ------------------------------------------
        def _generate_batch_clips(
            sections: str,
            output_dir: str = "",
            parallel: bool = True,
            **kwargs: Any,
        ) -> str:
            from vidmation.services.models.orchestrator import ModelOrchestrator

            orch = ModelOrchestrator(settings=self.settings)
            sections_list = json.loads(sections)
            out_dir = Path(output_dir) if output_dir else None
            results = orch.generate_batch(
                sections=sections_list,
                profile=self.profile,
                output_dir=out_dir,
                parallel=parallel,
            )
            return json.dumps(results, default=str)

        self._register(
            ToolDefinition(
                name="generate_batch_clips",
                description=(
                    "Generate video clips for all script sections using the model orchestrator. "
                    "Automatically routes each section to the best model based on content type."
                ),
                category="videogen",
                input_schema={
                    "type": "object",
                    "required": ["sections"],
                    "properties": {
                        "sections": {"type": "string", "description": "JSON array of script sections."},
                        "output_dir": {"type": "string", "description": "Directory for generated clips."},
                        "parallel": {"type": "boolean", "default": True, "description": "Generate clips in parallel."},
                    },
                },
                executor=_generate_batch_clips,
                cost_estimate=1.0,
            )
        )

        # -- estimate_video_cost -------------------------------------------
        def _estimate_video_cost(sections: str, **kwargs: Any) -> str:
            from vidmation.services.models.orchestrator import ModelOrchestrator

            orch = ModelOrchestrator(settings=self.settings)
            sections_list = json.loads(sections)
            estimate = orch.estimate_total_cost(sections_list)
            return json.dumps(estimate, default=str)

        self._register(
            ToolDefinition(
                name="estimate_video_cost",
                description="Estimate the total cost of generating video clips for all sections.",
                category="videogen",
                input_schema={
                    "type": "object",
                    "required": ["sections"],
                    "properties": {
                        "sections": {"type": "string", "description": "JSON array of script sections."},
                    },
                },
                executor=_estimate_video_cost,
                cost_estimate=0.0,
            )
        )

    # ===================================================================
    # VIDEO ASSEMBLY (6 tools)
    # ===================================================================

    def _register_assembly_tools(self) -> None:
        # -- assemble_full_video -------------------------------------------
        def _assemble_full_video(
            sections: str,
            voiceover_path: str,
            word_timestamps: str,
            music_path: str = "",
            output_path: str = "",
            work_dir: str = "",
            **kwargs: Any,
        ) -> str:
            from vidmation.video.assembler import VideoAssembler

            sections_list = json.loads(sections)
            words = json.loads(word_timestamps) if word_timestamps else []
            w_dir = Path(work_dir) if work_dir else Path("/tmp/vidmation_assembly")
            assembler = VideoAssembler(
                video_config=self.profile.video, work_dir=w_dir
            )
            out = Path(output_path) if output_path else None
            path = assembler.assemble(
                sections=sections_list,
                voiceover_path=Path(voiceover_path),
                word_timestamps=words,
                music_path=Path(music_path) if music_path else None,
                output_path=out,
            )
            return json.dumps({"path": str(path)})

        self._register(
            ToolDefinition(
                name="assemble_full_video",
                description=(
                    "Assemble the final video from all pipeline artifacts: clips, voiceover, "
                    "captions, and music. Handles clip fitting, transitions, audio mixing, "
                    "and caption burn-in in one step."
                ),
                category="assembly",
                input_schema={
                    "type": "object",
                    "required": ["sections", "voiceover_path", "word_timestamps"],
                    "properties": {
                        "sections": {"type": "string", "description": "JSON array of sections with media_path keys."},
                        "voiceover_path": {"type": "string", "description": "Path to voiceover audio."},
                        "word_timestamps": {"type": "string", "description": "JSON array of word timestamps."},
                        "music_path": {"type": "string", "description": "Optional background music path."},
                        "output_path": {"type": "string"},
                        "work_dir": {"type": "string", "description": "Working directory for intermediate files."},
                    },
                },
                executor=_assemble_full_video,
                cost_estimate=0.0,
            )
        )

        # -- mix_audio -----------------------------------------------------
        def _mix_audio(
            voiceover_path: str,
            music_path: str = "",
            music_volume: float = 0.15,
            output_path: str = "",
            **kwargs: Any,
        ) -> str:
            from vidmation.video.audio_mixer import mix_voiceover_and_music

            out = Path(output_path) if output_path else None
            path = mix_voiceover_and_music(
                voiceover_path=Path(voiceover_path),
                music_path=Path(music_path) if music_path else None,
                music_volume=music_volume,
                output_path=out,
            )
            return json.dumps({"path": str(path)})

        self._register(
            ToolDefinition(
                name="mix_audio",
                description="Mix voiceover with background music. Music is looped, volume-ducked, and faded.",
                category="assembly",
                input_schema={
                    "type": "object",
                    "required": ["voiceover_path"],
                    "properties": {
                        "voiceover_path": {"type": "string"},
                        "music_path": {"type": "string", "description": "Optional background music file."},
                        "music_volume": {"type": "number", "default": 0.15, "minimum": 0.0, "maximum": 1.0},
                        "output_path": {"type": "string"},
                    },
                },
                executor=_mix_audio,
                cost_estimate=0.0,
            )
        )

        # -- normalize_audio -----------------------------------------------
        def _normalize_audio(
            audio_path: str, target_lufs: float = -16.0, output_path: str = "", **kwargs: Any
        ) -> str:
            from vidmation.video.audio_mixer import normalize_audio

            out = Path(output_path) if output_path else None
            path = normalize_audio(
                audio_path=Path(audio_path), target_lufs=target_lufs, output_path=out
            )
            return json.dumps({"path": str(path)})

        self._register(
            ToolDefinition(
                name="normalize_audio",
                description="Loudness-normalize audio to a target LUFS using EBU R128 two-pass method.",
                category="assembly",
                input_schema={
                    "type": "object",
                    "required": ["audio_path"],
                    "properties": {
                        "audio_path": {"type": "string"},
                        "target_lufs": {"type": "number", "default": -16.0, "description": "Target loudness in LUFS."},
                        "output_path": {"type": "string"},
                    },
                },
                executor=_normalize_audio,
                cost_estimate=0.0,
            )
        )

        # -- fit_clip_to_duration ------------------------------------------
        def _fit_clip_to_duration(
            clip_path: str, duration: float, output_path: str = "", **kwargs: Any
        ) -> str:
            from vidmation.utils.ffmpeg import get_duration as _get_dur

            import ffmpeg as _ffmpeg

            src = Path(clip_path)
            out = Path(output_path) if output_path else src.with_stem(f"{src.stem}_fitted")
            out.parent.mkdir(parents=True, exist_ok=True)

            clip_dur = _get_dur(src)
            stream = _ffmpeg.input(str(src))
            if clip_dur > duration:
                stream = _ffmpeg.input(str(src), t=duration)
            elif clip_dur < duration * 0.5:
                speed = max(0.5, clip_dur / duration)
                stream = stream.filter("setpts", f"{1.0/speed}*PTS")

            try:
                stream.output(str(out), vcodec="libx264", pix_fmt="yuv420p", t=duration).overwrite_output().run(quiet=True)
            except _ffmpeg.Error as exc:
                stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
                return json.dumps({"error": f"Clip fitting failed: {stderr}"})
            return json.dumps({"path": str(out), "duration": duration})

        self._register(
            ToolDefinition(
                name="fit_clip_to_duration",
                description="Trim or speed-adjust a video clip to match a target duration.",
                category="assembly",
                input_schema={
                    "type": "object",
                    "required": ["clip_path", "duration"],
                    "properties": {
                        "clip_path": {"type": "string"},
                        "duration": {"type": "number", "minimum": 0.5},
                        "output_path": {"type": "string"},
                    },
                },
                executor=_fit_clip_to_duration,
                cost_estimate=0.0,
            )
        )

        # -- apply_ken_burns -----------------------------------------------
        def _apply_ken_burns(
            image_path: str, duration: float = 5.0, output_path: str = "", **kwargs: Any
        ) -> str:
            from vidmation.services.videogen.local_gen import LocalVideoGenerator

            gen = LocalVideoGenerator(settings=self.settings)
            out = Path(output_path) if output_path else None
            path = gen.generate_from_image(
                image_path=Path(image_path), prompt="ken burns zoom", duration=duration, output_path=out
            )
            return json.dumps({"path": str(path)})

        self._register(
            ToolDefinition(
                name="apply_ken_burns",
                description="Apply Ken Burns (slow zoom + pan) effect to a still image, producing a video clip.",
                category="assembly",
                input_schema={
                    "type": "object",
                    "required": ["image_path"],
                    "properties": {
                        "image_path": {"type": "string", "description": "Path to the source image."},
                        "duration": {"type": "number", "default": 5.0, "minimum": 1.0, "maximum": 60.0},
                        "output_path": {"type": "string"},
                    },
                },
                executor=_apply_ken_burns,
                cost_estimate=0.0,
            )
        )

        # -- encode_final --------------------------------------------------
        def _encode_final(
            video_path: str,
            format: str = "landscape",
            output_path: str = "",
            **kwargs: Any,
        ) -> str:
            import ffmpeg as _ffmpeg

            from vidmation.video.formats import get_format

            fmt = get_format(format)
            src = Path(video_path)
            out = Path(output_path) if output_path else src.with_stem(f"{src.stem}_final")
            out.parent.mkdir(parents=True, exist_ok=True)

            try:
                (
                    _ffmpeg.input(str(src))
                    .filter("scale", fmt.width, fmt.height, force_original_aspect_ratio="decrease")
                    .filter("pad", fmt.width, fmt.height, "(ow-iw)/2", "(oh-ih)/2", color="black")
                    .output(str(out), vcodec="libx264", crf="18", preset="medium", pix_fmt="yuv420p", movflags="+faststart")
                    .overwrite_output()
                    .run(quiet=True)
                )
            except _ffmpeg.Error as exc:
                stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
                return json.dumps({"error": f"Encoding failed: {stderr}"})
            return json.dumps({"path": str(out), "format": format, "resolution": f"{fmt.width}x{fmt.height}"})

        self._register(
            ToolDefinition(
                name="encode_final",
                description="Re-encode a video to a specific format (landscape, portrait, square) with proper resolution.",
                category="assembly",
                input_schema={
                    "type": "object",
                    "required": ["video_path"],
                    "properties": {
                        "video_path": {"type": "string"},
                        "format": {"type": "string", "enum": ["landscape", "portrait", "square"], "default": "landscape"},
                        "output_path": {"type": "string"},
                    },
                },
                executor=_encode_final,
                cost_estimate=0.0,
            )
        )

    # ===================================================================
    # CAPTIONS & SUBTITLES (5 tools)
    # ===================================================================

    def _register_caption_tools(self) -> None:
        # -- transcribe_whisper --------------------------------------------
        def _transcribe_whisper(
            audio_path: str, backend: str = "replicate", **kwargs: Any
        ) -> str:
            from vidmation.services.captions.whisper import WhisperCaptionGenerator

            gen = WhisperCaptionGenerator(settings=self.settings, backend=backend)
            words = gen.transcribe(Path(audio_path))
            return json.dumps(words)

        self._register(
            ToolDefinition(
                name="transcribe_whisper",
                description=(
                    "Transcribe audio to word-level timestamps using Whisper. "
                    "Returns array of {word, start, end} objects for caption generation."
                ),
                category="captions",
                input_schema={
                    "type": "object",
                    "required": ["audio_path"],
                    "properties": {
                        "audio_path": {"type": "string", "description": "Path to audio file (mp3/wav)."},
                        "backend": {"type": "string", "enum": ["replicate", "local"], "default": "replicate"},
                    },
                },
                executor=_transcribe_whisper,
                cost_estimate=0.006,
                requires_api_key="replicate_api_token",
            )
        )

        # -- list_caption_templates ----------------------------------------
        def _list_caption_templates(**kwargs: Any) -> str:
            from vidmation.captions.templates import list_templates

            templates = list_templates()
            return json.dumps(
                [{"name": t["name"], "display_name": t["display_name"], "description": t["description"]} for t in templates]
            )

        self._register(
            ToolDefinition(
                name="list_caption_templates",
                description="List all 41+ available caption animation templates with descriptions.",
                category="captions",
                input_schema={"type": "object", "properties": {}},
                executor=_list_caption_templates,
                cost_estimate=0.0,
            )
        )

        # -- apply_caption_template ----------------------------------------
        def _apply_caption_template(
            video_path: str,
            template_name: str,
            word_timestamps: str,
            output_path: str = "",
            **kwargs: Any,
        ) -> str:
            from vidmation.video.captions_render import render_with_template

            words = json.loads(word_timestamps)
            out = Path(output_path) if output_path else Path(video_path).with_stem(
                f"{Path(video_path).stem}_captioned"
            )
            path = render_with_template(
                words=words,
                template_name=template_name,
                video_path=Path(video_path),
                output_path=out,
            )
            return json.dumps({"path": str(path)})

        self._register(
            ToolDefinition(
                name="apply_caption_template",
                description=(
                    "Apply an animated caption template to a video. Supports 41+ styles "
                    "like 'hormozi', 'mrbeast', 'tiktok_viral', 'karaoke', etc."
                ),
                category="captions",
                input_schema={
                    "type": "object",
                    "required": ["video_path", "template_name", "word_timestamps"],
                    "properties": {
                        "video_path": {"type": "string"},
                        "template_name": {"type": "string", "description": "Caption template name (e.g. 'hormozi', 'mrbeast')."},
                        "word_timestamps": {"type": "string", "description": "JSON array of word timestamps."},
                        "output_path": {"type": "string"},
                    },
                },
                executor=_apply_caption_template,
                cost_estimate=0.0,
            )
        )

        # -- generate_ass_subtitles ----------------------------------------
        def _generate_ass_subtitles(
            word_timestamps: str,
            output_path: str,
            template_name: str = "hormozi",
            **kwargs: Any,
        ) -> str:
            from vidmation.video.captions_render import generate_animated_ass

            words = json.loads(word_timestamps)
            path = generate_animated_ass(
                words=words, output_path=Path(output_path), template_name=template_name
            )
            return json.dumps({"path": str(path)})

        self._register(
            ToolDefinition(
                name="generate_ass_subtitles",
                description="Generate an ASS subtitle file from word timestamps without burning into video.",
                category="captions",
                input_schema={
                    "type": "object",
                    "required": ["word_timestamps", "output_path"],
                    "properties": {
                        "word_timestamps": {"type": "string", "description": "JSON array of word timestamps."},
                        "output_path": {"type": "string", "description": "Path for the .ass file."},
                        "template_name": {"type": "string", "default": "hormozi"},
                    },
                },
                executor=_generate_ass_subtitles,
                cost_estimate=0.0,
            )
        )

        # -- burn_captions -------------------------------------------------
        def _burn_captions(
            video_path: str, ass_path: str, output_path: str, **kwargs: Any
        ) -> str:
            from vidmation.video.captions_render import burn_captions

            path = burn_captions(
                video_path=Path(video_path),
                ass_path=Path(ass_path),
                output_path=Path(output_path),
            )
            return json.dumps({"path": str(path)})

        self._register(
            ToolDefinition(
                name="burn_captions",
                description="Burn an ASS subtitle file into a video using ffmpeg's ass filter.",
                category="captions",
                input_schema={
                    "type": "object",
                    "required": ["video_path", "ass_path", "output_path"],
                    "properties": {
                        "video_path": {"type": "string"},
                        "ass_path": {"type": "string"},
                        "output_path": {"type": "string"},
                    },
                },
                executor=_burn_captions,
                cost_estimate=0.0,
            )
        )

    # ===================================================================
    # EFFECTS & POST-PROCESSING (8 tools)
    # ===================================================================

    def _register_effects_tools(self) -> None:
        # -- apply_magic_zoom ----------------------------------------------
        def _apply_magic_zoom(
            video_path: str,
            word_timestamps: str,
            style: str = "smooth",
            max_zooms: int = 10,
            output_path: str = "",
            **kwargs: Any,
        ) -> str:
            from vidmation.effects.magic_zoom import MagicZoom

            zoom = MagicZoom(settings=self.settings)
            words = json.loads(word_timestamps)
            out = Path(output_path) if output_path else Path(video_path).with_stem(
                f"{Path(video_path).stem}_zoomed"
            )
            result = zoom.apply(
                video_path=Path(video_path),
                word_timestamps=words,
                style=style,
                max_zooms=max_zooms,
                output_path=out,
            )
            return json.dumps(result, default=str)

        self._register(
            ToolDefinition(
                name="apply_magic_zoom",
                description=(
                    "Apply AI-powered auto-zoom at emphasis points in a video. "
                    "Detects key moments (statistics, emotional peaks, questions) and adds smooth zooms."
                ),
                category="effects",
                input_schema={
                    "type": "object",
                    "required": ["video_path", "word_timestamps"],
                    "properties": {
                        "video_path": {"type": "string"},
                        "word_timestamps": {"type": "string", "description": "JSON word timestamps."},
                        "style": {"type": "string", "enum": ["smooth", "crash", "expo", "linear"], "default": "smooth"},
                        "max_zooms": {"type": "integer", "default": 10, "minimum": 1, "maximum": 30},
                        "output_path": {"type": "string"},
                    },
                },
                executor=_apply_magic_zoom,
                cost_estimate=0.01,
                requires_api_key="anthropic_api_key",
            )
        )

        # -- detect_emphasis_points ----------------------------------------
        def _detect_emphasis_points(word_timestamps: str, **kwargs: Any) -> str:
            from vidmation.effects.magic_zoom import MagicZoom

            zoom = MagicZoom(settings=self.settings)
            words = json.loads(word_timestamps)
            points = zoom.detect_emphasis_points(words)
            return json.dumps(points, default=str)

        self._register(
            ToolDefinition(
                name="detect_emphasis_points",
                description="Detect emphasis points in a transcript for zoom effects (without applying them).",
                category="effects",
                input_schema={
                    "type": "object",
                    "required": ["word_timestamps"],
                    "properties": {
                        "word_timestamps": {"type": "string"},
                    },
                },
                executor=_detect_emphasis_points,
                cost_estimate=0.01,
                requires_api_key="anthropic_api_key",
            )
        )

        # -- remove_silence ------------------------------------------------
        def _remove_silence(
            video_path: str,
            mode: str = "normal",
            output_path: str = "",
            **kwargs: Any,
        ) -> str:
            from vidmation.effects.silence_remover import SilenceRemover

            remover = SilenceRemover()
            out = Path(output_path) if output_path else Path(video_path).with_stem(
                f"{Path(video_path).stem}_trimmed"
            )
            result = remover.remove_silence(
                video_path=Path(video_path), mode=mode, output_path=out
            )
            return json.dumps(result, default=str)

        self._register(
            ToolDefinition(
                name="remove_silence",
                description=(
                    "Remove silent segments from video. Modes: normal (800ms+), "
                    "fast (500ms+), extra_fast (300ms+). Returns trimmed video + stats."
                ),
                category="effects",
                input_schema={
                    "type": "object",
                    "required": ["video_path"],
                    "properties": {
                        "video_path": {"type": "string"},
                        "mode": {"type": "string", "enum": ["normal", "fast", "extra_fast"], "default": "normal"},
                        "output_path": {"type": "string"},
                    },
                },
                executor=_remove_silence,
                cost_estimate=0.0,
            )
        )

        # -- remove_filler_words -------------------------------------------
        def _remove_filler_words(
            video_path: str, word_timestamps: str, output_path: str = "", **kwargs: Any
        ) -> str:
            from vidmation.effects.silence_remover import SilenceRemover

            remover = SilenceRemover()
            words = json.loads(word_timestamps)
            out = Path(output_path) if output_path else Path(video_path).with_stem(
                f"{Path(video_path).stem}_nofiller"
            )
            result = remover.remove_filler_words(
                video_path=Path(video_path), word_timestamps=words, output_path=out
            )
            return json.dumps(result, default=str)

        self._register(
            ToolDefinition(
                name="remove_filler_words",
                description="Remove filler words (um, uh, like, basically, etc.) from video using word timestamps.",
                category="effects",
                input_schema={
                    "type": "object",
                    "required": ["video_path", "word_timestamps"],
                    "properties": {
                        "video_path": {"type": "string"},
                        "word_timestamps": {"type": "string"},
                        "output_path": {"type": "string"},
                    },
                },
                executor=_remove_filler_words,
                cost_estimate=0.0,
            )
        )

        # -- insert_broll --------------------------------------------------
        def _insert_broll(
            video_path: str,
            word_timestamps: str,
            max_clips: int = 5,
            output_path: str = "",
            **kwargs: Any,
        ) -> str:
            from vidmation.effects.magic_broll import MagicBRoll

            broll = MagicBRoll(settings=self.settings)
            words = json.loads(word_timestamps)
            out = Path(output_path) if output_path else Path(video_path).with_stem(
                f"{Path(video_path).stem}_broll"
            )
            result = broll.apply(
                video_path=Path(video_path),
                word_timestamps=words,
                max_clips=max_clips,
                output_path=out,
            )
            return json.dumps(result, default=str)

        self._register(
            ToolDefinition(
                name="insert_broll",
                description=(
                    "AI-powered contextual B-roll insertion. Analyzes transcript, "
                    "searches stock footage, and inserts matching clips at relevant moments."
                ),
                category="effects",
                input_schema={
                    "type": "object",
                    "required": ["video_path", "word_timestamps"],
                    "properties": {
                        "video_path": {"type": "string"},
                        "word_timestamps": {"type": "string"},
                        "max_clips": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
                        "output_path": {"type": "string"},
                    },
                },
                executor=_insert_broll,
                cost_estimate=0.02,
                requires_api_key="anthropic_api_key",
            )
        )

        # -- add_emojis ----------------------------------------------------
        def _add_emojis(
            video_path: str, word_timestamps: str, output_path: str = "", **kwargs: Any
        ) -> str:
            from vidmation.effects.emoji_sfx import EmojiSFXEngine

            engine = EmojiSFXEngine(settings=self.settings)
            words = json.loads(word_timestamps)
            out = Path(output_path) if output_path else Path(video_path).with_stem(
                f"{Path(video_path).stem}_emoji"
            )
            result = engine.add_emojis(
                video_path=Path(video_path), word_timestamps=words, output_path=out
            )
            return json.dumps(result, default=str)

        self._register(
            ToolDefinition(
                name="add_emojis",
                description="Add animated emoji overlays at keyword moments in the video.",
                category="effects",
                input_schema={
                    "type": "object",
                    "required": ["video_path", "word_timestamps"],
                    "properties": {
                        "video_path": {"type": "string"},
                        "word_timestamps": {"type": "string"},
                        "output_path": {"type": "string"},
                    },
                },
                executor=_add_emojis,
                cost_estimate=0.01,
            )
        )

        # -- add_sound_effects ---------------------------------------------
        def _add_sound_effects(
            audio_path: str, word_timestamps: str, output_path: str = "", **kwargs: Any
        ) -> str:
            from vidmation.effects.emoji_sfx import EmojiSFXEngine

            engine = EmojiSFXEngine(settings=self.settings)
            words = json.loads(word_timestamps)
            out = Path(output_path) if output_path else Path(audio_path).with_stem(
                f"{Path(audio_path).stem}_sfx"
            )
            result = engine.add_sound_effects(
                audio_path=Path(audio_path), word_timestamps=words, output_path=out
            )
            return json.dumps(result, default=str)

        self._register(
            ToolDefinition(
                name="add_sound_effects",
                description="Add contextual sound effects (ding, whoosh, pop, cash register, etc.) to audio.",
                category="effects",
                input_schema={
                    "type": "object",
                    "required": ["audio_path", "word_timestamps"],
                    "properties": {
                        "audio_path": {"type": "string"},
                        "word_timestamps": {"type": "string"},
                        "output_path": {"type": "string"},
                    },
                },
                executor=_add_sound_effects,
                cost_estimate=0.01,
                requires_api_key="anthropic_api_key",
            )
        )

        # -- extract_viral_clips -------------------------------------------
        def _extract_viral_clips(
            video_path: str,
            word_timestamps: str,
            count: int = 3,
            format: str = "9:16",
            output_dir: str = "",
            **kwargs: Any,
        ) -> str:
            from vidmation.effects.magic_clips import MagicClips

            clipper = MagicClips(settings=self.settings)
            words = json.loads(word_timestamps)
            out_dir = Path(output_dir) if output_dir else Path(video_path).parent / "clips"
            result = clipper.extract(
                video_path=Path(video_path),
                word_timestamps=words,
                count=count,
                target_format=format,
                output_dir=out_dir,
            )
            return json.dumps(result, default=str)

        self._register(
            ToolDefinition(
                name="extract_viral_clips",
                description=(
                    "Extract viral short-form clips from a long-form video. AI identifies "
                    "clip-worthy segments and extracts them with optional portrait reformatting."
                ),
                category="effects",
                input_schema={
                    "type": "object",
                    "required": ["video_path", "word_timestamps"],
                    "properties": {
                        "video_path": {"type": "string"},
                        "word_timestamps": {"type": "string"},
                        "count": {"type": "integer", "default": 3, "minimum": 1, "maximum": 10},
                        "format": {"type": "string", "enum": ["9:16", "16:9", "1:1"], "default": "9:16"},
                        "output_dir": {"type": "string"},
                    },
                },
                executor=_extract_viral_clips,
                cost_estimate=0.02,
                requires_api_key="anthropic_api_key",
            )
        )

    # ===================================================================
    # SEO & CONTENT (8 tools)
    # ===================================================================

    def _register_seo_tools(self) -> None:
        # -- optimize_title ------------------------------------------------
        def _optimize_title(title: str, topic: str = "", count: int = 5, **kwargs: Any) -> str:
            from vidmation.seo.optimizer import SEOOptimizer

            seo = SEOOptimizer(settings=self.settings)
            results = seo.optimize_titles(title=title, topic=topic or title, niche=self.profile.niche, count=count)
            return json.dumps(results, default=str)

        self._register(ToolDefinition(name="optimize_title", description="Generate SEO-optimized YouTube title variations with CTR scores.", category="seo", input_schema={"type": "object", "required": ["title"], "properties": {"title": {"type": "string"}, "topic": {"type": "string"}, "count": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20}}}, executor=_optimize_title, cost_estimate=0.01, requires_api_key="anthropic_api_key"))

        # -- optimize_description ------------------------------------------
        def _optimize_description(script: str, **kwargs: Any) -> str:
            from vidmation.seo.optimizer import SEOOptimizer

            seo = SEOOptimizer(settings=self.settings)
            script_dict = json.loads(script)
            result = seo.optimize_description(script=script_dict, profile=self.profile)
            return json.dumps(result, default=str)

        self._register(ToolDefinition(name="optimize_description", description="Generate a YouTube-optimized description with timestamps, keywords, and CTAs.", category="seo", input_schema={"type": "object", "required": ["script"], "properties": {"script": {"type": "string", "description": "Script JSON string."}}}, executor=_optimize_description, cost_estimate=0.01, requires_api_key="anthropic_api_key"))

        # -- generate_tags -------------------------------------------------
        def _generate_tags(script: str, **kwargs: Any) -> str:
            from vidmation.seo.optimizer import SEOOptimizer

            seo = SEOOptimizer(settings=self.settings)
            script_dict = json.loads(script)
            tags = seo.generate_tags(script=script_dict)
            return json.dumps(tags)

        self._register(ToolDefinition(name="generate_tags", description="Generate optimized YouTube tags from a video script.", category="seo", input_schema={"type": "object", "required": ["script"], "properties": {"script": {"type": "string"}}}, executor=_generate_tags, cost_estimate=0.01, requires_api_key="anthropic_api_key"))

        # -- generate_hashtags ---------------------------------------------
        def _generate_hashtags(script: str, platform: str = "youtube", **kwargs: Any) -> str:
            from vidmation.seo.hashtags import HashtagGenerator

            gen = HashtagGenerator(settings=self.settings)
            script_dict = json.loads(script)
            hashtags = gen.generate(script=script_dict, platform=platform)
            return json.dumps(hashtags, default=str)

        self._register(ToolDefinition(name="generate_hashtags", description="Generate platform-specific hashtags (YouTube, TikTok, or Instagram).", category="seo", input_schema={"type": "object", "required": ["script"], "properties": {"script": {"type": "string"}, "platform": {"type": "string", "enum": ["youtube", "tiktok", "instagram"], "default": "youtube"}}}, executor=_generate_hashtags, cost_estimate=0.01, requires_api_key="anthropic_api_key"))

        # -- keyword_research ----------------------------------------------
        def _keyword_research(topic: str, niche: str = "", **kwargs: Any) -> str:
            from vidmation.seo.optimizer import SEOOptimizer

            seo = SEOOptimizer(settings=self.settings)
            result = seo.keyword_research(topic=topic, niche=niche or self.profile.niche)
            return json.dumps(result, default=str)

        self._register(ToolDefinition(name="keyword_research", description="Research keyword opportunities for a topic and niche.", category="seo", input_schema={"type": "object", "required": ["topic"], "properties": {"topic": {"type": "string"}, "niche": {"type": "string"}}}, executor=_keyword_research, cost_estimate=0.01, requires_api_key="anthropic_api_key"))

        # -- generate_content_calendar -------------------------------------
        def _generate_content_calendar(weeks: int = 4, **kwargs: Any) -> str:
            from vidmation.content.planner import ContentPlanner

            planner = ContentPlanner(settings=self.settings)
            calendar = planner.generate_calendar(channel=self.profile, weeks=weeks)
            return json.dumps(calendar, default=str)

        self._register(ToolDefinition(name="generate_content_calendar", description="Generate an AI-powered content calendar for the channel.", category="seo", input_schema={"type": "object", "properties": {"weeks": {"type": "integer", "default": 4, "minimum": 1, "maximum": 12}}}, executor=_generate_content_calendar, cost_estimate=0.02, requires_api_key="anthropic_api_key"))

        # -- suggest_trending_topics ---------------------------------------
        def _suggest_trending_topics(niche: str = "", count: int = 10, **kwargs: Any) -> str:
            from vidmation.content.planner import ContentPlanner

            planner = ContentPlanner(settings=self.settings)
            topics = planner.suggest_trending(niche=niche or self.profile.niche, count=count)
            return json.dumps(topics, default=str)

        self._register(ToolDefinition(name="suggest_trending_topics", description="Suggest trending video topics for a niche.", category="seo", input_schema={"type": "object", "properties": {"niche": {"type": "string"}, "count": {"type": "integer", "default": 10, "minimum": 1, "maximum": 30}}}, executor=_suggest_trending_topics, cost_estimate=0.01, requires_api_key="anthropic_api_key"))

        # -- analyze_content_gaps ------------------------------------------
        def _analyze_content_gaps(**kwargs: Any) -> str:
            from vidmation.content.planner import ContentPlanner

            planner = ContentPlanner(settings=self.settings)
            gaps = planner.analyze_gaps(channel=self.profile)
            return json.dumps(gaps, default=str)

        self._register(ToolDefinition(name="analyze_content_gaps", description="Analyze content gaps for the channel -- find untapped topics and underserved angles.", category="seo", input_schema={"type": "object", "properties": {}}, executor=_analyze_content_gaps, cost_estimate=0.02, requires_api_key="anthropic_api_key"))

    # ===================================================================
    # BRAND & TEMPLATES (5 tools)
    # ===================================================================

    def _register_brand_tools(self) -> None:
        # -- apply_brand_kit -----------------------------------------------
        def _apply_brand_kit(video_path: str, output_path: str = "", **kwargs: Any) -> str:
            from vidmation.brand.kit import BrandKit

            kit = BrandKit.from_profile(self.profile) if hasattr(BrandKit, "from_profile") else BrandKit()
            out = Path(output_path) if output_path else Path(video_path).with_stem(f"{Path(video_path).stem}_branded")
            result = kit.apply_to_video(video_path=Path(video_path), output_path=out)
            return json.dumps({"path": str(result)}, default=str)

        self._register(ToolDefinition(name="apply_brand_kit", description="Apply full brand kit to a video: logo overlay, watermark, intro/outro clips.", category="brand", input_schema={"type": "object", "required": ["video_path"], "properties": {"video_path": {"type": "string"}, "output_path": {"type": "string"}}}, executor=_apply_brand_kit, cost_estimate=0.0))

        # -- add_logo_overlay ----------------------------------------------
        def _add_logo_overlay(video_path: str, position: str = "top_right", opacity: float = 0.8, output_path: str = "", **kwargs: Any) -> str:
            from vidmation.brand.overlays import add_logo_overlay

            out = Path(output_path) if output_path else Path(video_path).with_stem(f"{Path(video_path).stem}_logo")
            path = add_logo_overlay(video_path=Path(video_path), position=position, opacity=opacity, output_path=out)
            return json.dumps({"path": str(path)})

        self._register(ToolDefinition(name="add_logo_overlay", description="Add a logo overlay to a video at a specified position.", category="brand", input_schema={"type": "object", "required": ["video_path"], "properties": {"video_path": {"type": "string"}, "position": {"type": "string", "enum": ["top_left", "top_right", "bottom_left", "bottom_right", "center"], "default": "top_right"}, "opacity": {"type": "number", "default": 0.8, "minimum": 0.0, "maximum": 1.0}, "output_path": {"type": "string"}}}, executor=_add_logo_overlay, cost_estimate=0.0))

        # -- add_lower_third -----------------------------------------------
        def _add_lower_third(video_path: str, text: str, style: str = "default", output_path: str = "", **kwargs: Any) -> str:
            from vidmation.brand.overlays import add_lower_third

            out = Path(output_path) if output_path else Path(video_path).with_stem(f"{Path(video_path).stem}_lt")
            path = add_lower_third(video_path=Path(video_path), text=text, style=style, output_path=out)
            return json.dumps({"path": str(path)})

        self._register(ToolDefinition(name="add_lower_third", description="Add a lower-third name/title overlay to a video.", category="brand", input_schema={"type": "object", "required": ["video_path", "text"], "properties": {"video_path": {"type": "string"}, "text": {"type": "string", "description": "Text to display."}, "style": {"type": "string", "default": "default"}, "output_path": {"type": "string"}}}, executor=_add_lower_third, cost_estimate=0.0))

        # -- list_video_templates ------------------------------------------
        def _list_video_templates(**kwargs: Any) -> str:
            from vidmation.brand.templates import list_templates

            templates = list_templates()
            return json.dumps(templates, default=str)

        self._register(ToolDefinition(name="list_video_templates", description="List all available video production templates.", category="brand", input_schema={"type": "object", "properties": {}}, executor=_list_video_templates, cost_estimate=0.0))

        # -- apply_video_template ------------------------------------------
        def _apply_video_template(template_name: str, **kwargs: Any) -> str:
            from vidmation.brand.templates import get_template

            config = get_template(template_name)
            return json.dumps(config, default=str)

        self._register(ToolDefinition(name="apply_video_template", description="Load a video production template configuration by name.", category="brand", input_schema={"type": "object", "required": ["template_name"], "properties": {"template_name": {"type": "string"}}}, executor=_apply_video_template, cost_estimate=0.0))

    # ===================================================================
    # PLATFORM EXPORT (5 tools)
    # ===================================================================

    def _register_platform_tools(self) -> None:
        def _make_export_tool(platform_name: str, description: str) -> Callable[..., str]:
            def _export(video_path: str, output_dir: str = "", **kwargs: Any) -> str:
                from vidmation.platforms.exporter import MultiPlatformExporter

                exporter = MultiPlatformExporter()
                out_dir = Path(output_dir) if output_dir else Path(video_path).parent / "exports"
                results = exporter.export(video_path=Path(video_path), platforms=[platform_name], output_dir=out_dir)
                return json.dumps({k: str(v) for k, v in results.items()}, default=str)

            return _export

        schema_base = {"type": "object", "required": ["video_path"], "properties": {"video_path": {"type": "string"}, "output_dir": {"type": "string"}}}

        self._register(ToolDefinition(name="export_youtube", description="Export video in YouTube-ready format (1920x1080 landscape).", category="platform", input_schema=schema_base, executor=_make_export_tool("youtube"), cost_estimate=0.0))
        self._register(ToolDefinition(name="export_tiktok", description="Export video for TikTok (9:16 portrait, cropped/padded).", category="platform", input_schema=schema_base, executor=_make_export_tool("tiktok"), cost_estimate=0.0))
        self._register(ToolDefinition(name="export_instagram_reels", description="Export video for Instagram Reels (9:16 portrait).", category="platform", input_schema=schema_base, executor=_make_export_tool("instagram_reels"), cost_estimate=0.0))
        self._register(ToolDefinition(name="export_instagram_feed", description="Export video for Instagram Feed (1:1 square).", category="platform", input_schema=schema_base, executor=_make_export_tool("instagram_feed"), cost_estimate=0.0))

        # -- export_all_platforms ------------------------------------------
        def _export_all_platforms(video_path: str, platforms: list[str] | None = None, output_dir: str = "", **kwargs: Any) -> str:
            from vidmation.platforms.exporter import MultiPlatformExporter

            exporter = MultiPlatformExporter()
            out_dir = Path(output_dir) if output_dir else Path(video_path).parent / "exports"
            plats = platforms or ["youtube", "tiktok", "instagram_reels"]
            results = exporter.export(video_path=Path(video_path), platforms=plats, output_dir=out_dir)
            return json.dumps({k: str(v) for k, v in results.items()}, default=str)

        self._register(ToolDefinition(
            name="export_all_platforms",
            description="Export video for multiple platforms at once. Returns a dict of platform -> file path.",
            category="platform",
            input_schema={
                "type": "object",
                "required": ["video_path"],
                "properties": {
                    "video_path": {"type": "string"},
                    "platforms": {"type": "array", "items": {"type": "string"}, "description": "Platform names (default: youtube, tiktok, instagram_reels)."},
                    "output_dir": {"type": "string"},
                },
            },
            executor=_export_all_platforms,
            cost_estimate=0.0,
        ))

    # ===================================================================
    # YOUTUBE (4 tools)
    # ===================================================================

    def _register_youtube_tools(self) -> None:
        # -- upload_to_youtube ---------------------------------------------
        def _upload_to_youtube(video_path: str, title: str, description: str, tags: list[str] | None = None, visibility: str = "private", thumbnail_path: str = "", **kwargs: Any) -> str:
            from vidmation.services.youtube.auth import get_credentials
            from vidmation.services.youtube.uploader import YouTubeUploader

            token_path = Path.home() / ".vidmation" / "youtube_token.json"
            secret_path = Path.home() / ".vidmation" / "client_secret.json"
            creds = get_credentials(token_path=token_path, client_secret_path=secret_path)
            uploader = YouTubeUploader(credentials=creds)
            video_id = uploader.upload(
                video_path=Path(video_path), title=title, description=description,
                tags=tags, visibility=visibility,
                thumbnail_path=Path(thumbnail_path) if thumbnail_path else None,
            )
            return json.dumps({"video_id": video_id, "url": f"https://youtube.com/watch?v={video_id}"})

        self._register(ToolDefinition(name="upload_to_youtube", description="Upload a video to YouTube with title, description, tags, and optional thumbnail.", category="youtube", input_schema={"type": "object", "required": ["video_path", "title", "description"], "properties": {"video_path": {"type": "string"}, "title": {"type": "string", "maxLength": 100}, "description": {"type": "string", "maxLength": 5000}, "tags": {"type": "array", "items": {"type": "string"}}, "visibility": {"type": "string", "enum": ["public", "unlisted", "private"], "default": "private"}, "thumbnail_path": {"type": "string"}}}, executor=_upload_to_youtube, cost_estimate=0.0))

        # -- set_youtube_thumbnail -----------------------------------------
        def _set_youtube_thumbnail(video_id: str, thumbnail_path: str, **kwargs: Any) -> str:
            from vidmation.services.youtube.auth import get_credentials
            from vidmation.services.youtube.uploader import YouTubeUploader

            token_path = Path.home() / ".vidmation" / "youtube_token.json"
            secret_path = Path.home() / ".vidmation" / "client_secret.json"
            creds = get_credentials(token_path=token_path, client_secret_path=secret_path)
            uploader = YouTubeUploader(credentials=creds)
            uploader._set_thumbnail(video_id, Path(thumbnail_path))
            return json.dumps({"success": True, "video_id": video_id})

        self._register(ToolDefinition(name="set_youtube_thumbnail", description="Set or update the thumbnail for an uploaded YouTube video.", category="youtube", input_schema={"type": "object", "required": ["video_id", "thumbnail_path"], "properties": {"video_id": {"type": "string"}, "thumbnail_path": {"type": "string"}}}, executor=_set_youtube_thumbnail, cost_estimate=0.0))

        # -- get_youtube_analytics -----------------------------------------
        def _get_youtube_analytics(video_id: str, **kwargs: Any) -> str:
            from vidmation.analytics.youtube_analytics import YouTubeAnalyticsFetcher

            fetcher = YouTubeAnalyticsFetcher()
            stats = fetcher.fetch_video_stats(video_id=video_id)
            return json.dumps(stats, default=str)

        self._register(ToolDefinition(name="get_youtube_analytics", description="Fetch performance analytics for a YouTube video (views, likes, comments, retention).", category="youtube", input_schema={"type": "object", "required": ["video_id"], "properties": {"video_id": {"type": "string"}}}, executor=_get_youtube_analytics, cost_estimate=0.0))

        # -- schedule_youtube_publish --------------------------------------
        def _schedule_youtube_publish(video_id: str, publish_at: str, **kwargs: Any) -> str:
            from vidmation.publishing.manager import PublishManager

            pm = PublishManager()
            from datetime import datetime

            dt = datetime.fromisoformat(publish_at)
            result = pm.publish(video_id=video_id, platforms=["youtube"], schedule_at=dt)
            return json.dumps(result, default=str)

        self._register(ToolDefinition(name="schedule_youtube_publish", description="Schedule a YouTube video for future publication.", category="youtube", input_schema={"type": "object", "required": ["video_id", "publish_at"], "properties": {"video_id": {"type": "string"}, "publish_at": {"type": "string", "description": "ISO 8601 datetime for publishing."}}}, executor=_schedule_youtube_publish, cost_estimate=0.0))

    # ===================================================================
    # ANALYTICS & TRACKING (5 tools)
    # ===================================================================

    def _register_analytics_tools(self) -> None:
        # -- estimate_total_cost -------------------------------------------
        def _estimate_total_cost(sections: str, **kwargs: Any) -> str:
            from vidmation.services.models.orchestrator import ModelOrchestrator

            orch = ModelOrchestrator(settings=self.settings)
            sections_list = json.loads(sections)
            estimate = orch.estimate_total_cost(sections_list)
            return json.dumps(estimate, default=str)

        self._register(ToolDefinition(name="estimate_total_cost", description="Estimate total production cost for a video based on its script sections.", category="analytics", input_schema={"type": "object", "required": ["sections"], "properties": {"sections": {"type": "string"}}}, executor=_estimate_total_cost, cost_estimate=0.0))

        # -- track_api_usage -----------------------------------------------
        def _track_api_usage(service: str, operation: str, cost: float = 0.0, **kwargs: Any) -> str:
            from vidmation.analytics.tracker import get_tracker

            tracker = get_tracker()
            event = tracker.track(service=service, operation=operation, cost_usd=cost, **kwargs)
            return json.dumps({"event_id": str(event.id), "cost_usd": cost})

        self._register(ToolDefinition(name="track_api_usage", description="Log an API usage event with service name, operation, and cost.", category="analytics", input_schema={"type": "object", "required": ["service", "operation"], "properties": {"service": {"type": "string"}, "operation": {"type": "string"}, "cost": {"type": "number", "default": 0.0}}}, executor=_track_api_usage, cost_estimate=0.0))

        # -- get_cost_summary ----------------------------------------------
        def _get_cost_summary(period: str = "monthly", **kwargs: Any) -> str:
            from vidmation.analytics.reports import ReportGenerator

            gen = ReportGenerator()
            report = gen.cost_report(period=period)
            return json.dumps(report, default=str)

        self._register(ToolDefinition(name="get_cost_summary", description="Get a cost breakdown report for a period (daily, weekly, monthly).", category="analytics", input_schema={"type": "object", "properties": {"period": {"type": "string", "enum": ["daily", "weekly", "monthly"], "default": "monthly"}}}, executor=_get_cost_summary, cost_estimate=0.0))

        # -- get_video_cost ------------------------------------------------
        def _get_video_cost(video_id: str, **kwargs: Any) -> str:
            from vidmation.analytics.reports import ReportGenerator

            gen = ReportGenerator()
            cost = gen.video_cost_report(video_id=video_id)
            return json.dumps(cost, default=str)

        self._register(ToolDefinition(name="get_video_cost", description="Get the per-video cost breakdown for a specific video.", category="analytics", input_schema={"type": "object", "required": ["video_id"], "properties": {"video_id": {"type": "string"}}}, executor=_get_video_cost, cost_estimate=0.0))

        # -- generate_efficiency_report ------------------------------------
        def _generate_efficiency_report(**kwargs: Any) -> str:
            from vidmation.analytics.reports import ReportGenerator

            gen = ReportGenerator()
            report = gen.efficiency_report()
            return json.dumps(report, default=str)

        self._register(ToolDefinition(name="generate_efficiency_report", description="Generate an ROI/efficiency report: cost-per-video, cost-per-view, production time trends.", category="analytics", input_schema={"type": "object", "properties": {}}, executor=_generate_efficiency_report, cost_estimate=0.0))

    # ===================================================================
    # DATABASE OPERATIONS (6 tools)
    # ===================================================================

    def _register_db_tools(self) -> None:
        # -- create_channel ------------------------------------------------
        def _create_channel(name: str, **kwargs: Any) -> str:
            from vidmation.db.engine import get_session
            from vidmation.db.repos import ChannelRepo

            session = get_session()
            try:
                repo = ChannelRepo(session)
                channel = repo.create(name=name, **kwargs)
                return json.dumps({"id": channel.id, "name": channel.name}, default=str)
            finally:
                session.close()

        self._register(ToolDefinition(name="create_channel", description="Create a new channel record in the database.", category="db", input_schema={"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}, "niche": {"type": "string"}, "target_audience": {"type": "string"}}}, executor=_create_channel, cost_estimate=0.0))

        # -- list_channels -------------------------------------------------
        def _list_channels(**kwargs: Any) -> str:
            from vidmation.db.engine import get_session
            from vidmation.db.repos import ChannelRepo

            session = get_session()
            try:
                repo = ChannelRepo(session)
                channels = repo.list_all()
                return json.dumps([{"id": c.id, "name": c.name} for c in channels], default=str)
            finally:
                session.close()

        self._register(ToolDefinition(name="list_channels", description="List all channels in the database.", category="db", input_schema={"type": "object", "properties": {}}, executor=_list_channels, cost_estimate=0.0))

        # -- create_video_record -------------------------------------------
        def _create_video_record(topic: str, channel_id: str = "", **kwargs: Any) -> str:
            from vidmation.db.engine import get_session
            from vidmation.db.repos import VideoRepo

            session = get_session()
            try:
                repo = VideoRepo(session)
                video = repo.create(topic=topic, channel_id=channel_id or None, **kwargs)
                return json.dumps({"id": video.id, "topic": video.topic, "status": str(video.status)}, default=str)
            finally:
                session.close()

        self._register(ToolDefinition(name="create_video_record", description="Create a new video record in the database.", category="db", input_schema={"type": "object", "required": ["topic"], "properties": {"topic": {"type": "string"}, "channel_id": {"type": "string"}}}, executor=_create_video_record, cost_estimate=0.0))

        # -- update_video_status -------------------------------------------
        def _update_video_status(video_id: str, status: str, **kwargs: Any) -> str:
            from vidmation.db.engine import get_session
            from vidmation.db.repos import VideoRepo
            from vidmation.models.video import VideoStatus

            session = get_session()
            try:
                repo = VideoRepo(session)
                vs = VideoStatus(status)
                video = repo.update_status(video_id, vs, **kwargs)
                if video is None:
                    return json.dumps({"error": f"Video {video_id} not found"})
                return json.dumps({"id": video.id, "status": str(video.status)}, default=str)
            finally:
                session.close()

        self._register(ToolDefinition(name="update_video_status", description="Update the status of a video record.", category="db", input_schema={"type": "object", "required": ["video_id", "status"], "properties": {"video_id": {"type": "string"}, "status": {"type": "string", "enum": ["draft", "scripted", "generating", "assembling", "reviewing", "ready", "published", "failed"]}}}, executor=_update_video_status, cost_estimate=0.0))

        # -- create_job ----------------------------------------------------
        def _create_job(video_id: str, job_type: str = "full_pipeline", **kwargs: Any) -> str:
            from vidmation.db.engine import get_session
            from vidmation.db.repos import JobRepo

            session = get_session()
            try:
                repo = JobRepo(session)
                job = repo.create(video_id=video_id, job_type=job_type, **kwargs)
                return json.dumps({"id": job.id, "video_id": video_id, "status": str(job.status)}, default=str)
            finally:
                session.close()

        self._register(ToolDefinition(name="create_job", description="Create a pipeline job record for a video.", category="db", input_schema={"type": "object", "required": ["video_id"], "properties": {"video_id": {"type": "string"}, "job_type": {"type": "string", "default": "full_pipeline"}}}, executor=_create_job, cost_estimate=0.0))

        # -- list_recent_videos --------------------------------------------
        def _list_recent_videos(limit: int = 20, **kwargs: Any) -> str:
            from vidmation.db.engine import get_session
            from vidmation.db.repos import VideoRepo

            session = get_session()
            try:
                repo = VideoRepo(session)
                videos = repo.list_all(limit=limit)
                return json.dumps([{"id": v.id, "topic": v.topic, "status": str(v.status)} for v in videos], default=str)
            finally:
                session.close()

        self._register(ToolDefinition(name="list_recent_videos", description="List recent videos from the database.", category="db", input_schema={"type": "object", "properties": {"limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100}}}, executor=_list_recent_videos, cost_estimate=0.0))

    # ===================================================================
    # NOTIFICATIONS & SCHEDULING (4 tools)
    # ===================================================================

    def _register_notification_tools(self) -> None:
        # -- send_notification ---------------------------------------------
        def _send_notification(event: str, title: str, message: str, **kwargs: Any) -> str:
            from vidmation.notifications.manager import NotificationManager

            mgr = NotificationManager()
            notif = mgr.notify(event=event, title=title, message=message, data=kwargs.get("data"))
            return json.dumps({"id": str(notif.id), "event": event, "title": title}, default=str)

        self._register(ToolDefinition(name="send_notification", description="Send a notification via all configured channels (email, Discord, Slack).", category="notifications", input_schema={"type": "object", "required": ["event", "title", "message"], "properties": {"event": {"type": "string", "description": "Event name (e.g. video_complete, job_failed)."}, "title": {"type": "string"}, "message": {"type": "string"}}}, executor=_send_notification, cost_estimate=0.0))

        # -- schedule_video ------------------------------------------------
        def _schedule_video(video_id: str, publish_at: str, platforms: list[str] | None = None, **kwargs: Any) -> str:
            from datetime import datetime

            from vidmation.publishing.manager import PublishManager

            pm = PublishManager()
            dt = datetime.fromisoformat(publish_at)
            plats = platforms or ["youtube"]
            result = pm.publish(video_id=video_id, platforms=plats, schedule_at=dt)
            return json.dumps(result, default=str)

        self._register(ToolDefinition(name="schedule_video", description="Schedule a video for future publishing on one or more platforms.", category="notifications", input_schema={"type": "object", "required": ["video_id", "publish_at"], "properties": {"video_id": {"type": "string"}, "publish_at": {"type": "string", "description": "ISO 8601 datetime."}, "platforms": {"type": "array", "items": {"type": "string"}, "description": "Platforms to publish to."}}}, executor=_schedule_video, cost_estimate=0.0))

        # -- create_recurring_schedule -------------------------------------
        def _create_recurring_schedule(channel_id: str, cron: str, topic_source: str = "ai", **kwargs: Any) -> str:
            from vidmation.scheduling.advanced import AdvancedScheduler

            scheduler = AdvancedScheduler()
            result = scheduler.create_recurring(channel_id=channel_id, cron_expression=cron, topic_source=topic_source)
            return json.dumps(result, default=str)

        self._register(ToolDefinition(name="create_recurring_schedule", description="Create a recurring video generation schedule using a cron expression.", category="notifications", input_schema={"type": "object", "required": ["channel_id", "cron"], "properties": {"channel_id": {"type": "string"}, "cron": {"type": "string", "description": "Cron expression (e.g. '0 10 * * mon,wed,fri')."}, "topic_source": {"type": "string", "enum": ["ai", "calendar", "manual"], "default": "ai"}}}, executor=_create_recurring_schedule, cost_estimate=0.0))

        # -- get_upcoming_schedule -----------------------------------------
        def _get_upcoming_schedule(**kwargs: Any) -> str:
            from vidmation.scheduling.advanced import AdvancedScheduler

            scheduler = AdvancedScheduler()
            upcoming = scheduler.get_upcoming(limit=20)
            return json.dumps(upcoming, default=str)

        self._register(ToolDefinition(name="get_upcoming_schedule", description="Get upcoming scheduled video generation and publishing items.", category="notifications", input_schema={"type": "object", "properties": {}}, executor=_get_upcoming_schedule, cost_estimate=0.0))

    # ===================================================================
    # FILE & SYSTEM (4 tools)
    # ===================================================================

    def _register_file_tools(self) -> None:
        # -- check_ffmpeg --------------------------------------------------
        def _check_ffmpeg(**kwargs: Any) -> str:
            from vidmation.utils.ffmpeg import check_ffmpeg_installed

            import shutil

            ok = check_ffmpeg_installed()
            version = "unknown"
            ffmpeg_path = shutil.which("ffmpeg")
            if ffmpeg_path:
                import subprocess

                try:
                    result = subprocess.run([ffmpeg_path, "-version"], capture_output=True, text=True, timeout=5)
                    first_line = result.stdout.split("\n")[0] if result.stdout else "unknown"
                    version = first_line
                except Exception:
                    pass
            return json.dumps({"installed": ok, "version": version, "path": ffmpeg_path or ""})

        self._register(ToolDefinition(name="check_ffmpeg", description="Check if ffmpeg is installed and return its version.", category="file", input_schema={"type": "object", "properties": {}}, executor=_check_ffmpeg, cost_estimate=0.0))

        # -- get_audio_duration --------------------------------------------
        def _get_audio_duration(path: str, **kwargs: Any) -> str:
            from vidmation.utils.ffmpeg import get_duration

            duration = get_duration(Path(path))
            return json.dumps({"path": path, "duration_seconds": duration})

        self._register(ToolDefinition(name="get_audio_duration", description="Get the duration of an audio or video file in seconds.", category="file", input_schema={"type": "object", "required": ["path"], "properties": {"path": {"type": "string"}}}, executor=_get_audio_duration, cost_estimate=0.0))

        # -- get_video_resolution ------------------------------------------
        def _get_video_resolution(path: str, **kwargs: Any) -> str:
            from vidmation.utils.ffmpeg import get_resolution

            width, height = get_resolution(Path(path))
            return json.dumps({"path": path, "width": width, "height": height})

        self._register(ToolDefinition(name="get_video_resolution", description="Get the width and height of a video file.", category="file", input_schema={"type": "object", "required": ["path"], "properties": {"path": {"type": "string"}}}, executor=_get_video_resolution, cost_estimate=0.0))

        # -- create_work_directory -----------------------------------------
        def _create_work_directory(video_id: str, **kwargs: Any) -> str:
            from vidmation.utils.files import get_work_dir

            work_dir = get_work_dir(video_id)
            return json.dumps({"path": str(work_dir), "video_id": video_id})

        self._register(ToolDefinition(name="create_work_directory", description="Create and return a working directory for a video's pipeline artifacts.", category="file", input_schema={"type": "object", "required": ["video_id"], "properties": {"video_id": {"type": "string"}}}, executor=_create_work_directory, cost_estimate=0.0))
