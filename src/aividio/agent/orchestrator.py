"""AI Agent Orchestrator - Claude coordinates video creation end-to-end.

Instead of rigid pipeline stages, the AI agent:
1. Analyzes the video topic and creates a comprehensive production plan
2. Makes intelligent decisions about which services, models, and effects to use
3. Coordinates execution of each step, adapting based on intermediate results
4. Handles errors by trying alternative approaches
5. Optimises for quality, cost, and speed based on profile settings
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import anthropic

from aividio.agent.prompts import (
    PRODUCTION_PLAN_PROMPT,
    REVIEW_PROMPT,
    SYSTEM_PROMPT,
)
from aividio.agent.tools import AgentToolkit
from aividio.config.profiles import ChannelProfile, get_default_profile
from aividio.config.settings import Settings, get_settings
from aividio.models.video import VideoFormat
from aividio.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)

# Maximum agent iterations to prevent infinite loops
MAX_AGENT_ITERATIONS = 50

# Claude model to use for the agent
AGENT_MODEL = "claude-sonnet-4-20250514"


class AgentOrchestrator:
    """AI-powered video production orchestrator using Claude.

    Instead of running a fixed sequence of stages, the agent analyzes the
    video topic, creates a production plan, and executes it step by step,
    making intelligent decisions at each point.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        api_key = self.settings.anthropic_api_key.get_secret_value()
        if not api_key:
            raise ValueError(
                "anthropic_api_key is required for the AI agent. "
                "Set VIDMATION_ANTHROPIC_API_KEY in your environment."
            )
        self.client = anthropic.Anthropic(api_key=api_key)
        self.tools = self._build_tool_definitions()
        self.conversation_history: list[dict[str, Any]] = []
        self._step_callback: Any = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_video(
        self,
        topic: str,
        channel_profile: ChannelProfile | None = None,
        target_duration: str = "10-12 minutes",
        format: str = "landscape",
        upload: bool = False,
        budget_limit: float | None = None,
        step_callback: Any = None,
    ) -> PipelineContext:
        """Let the AI agent orchestrate complete video creation.

        Args:
            topic: The video topic or prompt.
            channel_profile: Channel configuration. Defaults to the default profile.
            target_duration: Target video duration (e.g. "10-12 minutes").
            format: Video format ("landscape", "portrait", "short").
            upload: Whether to upload to YouTube when done.
            budget_limit: Maximum budget in USD (None = no limit).
            step_callback: Optional callback ``(step_name: str, detail: str) -> None``
                called each time the agent completes a tool call.

        Returns:
            The completed PipelineContext with all artifacts.
        """
        profile = channel_profile or get_default_profile()
        self._step_callback = step_callback

        # Create pipeline context
        video_id = str(uuid.uuid4())
        work_dir = self.settings.output_dir / video_id
        work_dir.mkdir(parents=True, exist_ok=True)

        video_format = VideoFormat(format) if format in ("landscape", "portrait", "short") else VideoFormat.LANDSCAPE

        ctx = PipelineContext(
            video_id=video_id,
            channel_profile=profile,
            topic=topic,
            format=video_format,
            work_dir=work_dir,
        )

        # Get available caption template names for the prompt
        try:
            from aividio.captions.templates import list_templates
            template_names = ", ".join(t["name"] for t in list_templates()[:20])
        except Exception:
            template_names = "bold_centered, hormozi, mrbeast, finance_serious, tech_modern, motivation_fire, education_clear"

        # Build the initial prompt
        budget_str = f"${budget_limit:.2f}" if budget_limit else "No limit"
        initial_message = PRODUCTION_PLAN_PROMPT.format(
            topic=topic,
            channel_name=profile.name,
            niche=profile.niche,
            target_audience=profile.target_audience,
            tone=profile.content.tone,
            target_duration=target_duration,
            format=format,
            budget_limit=budget_str,
            script_style=profile.content.script_style,
            hook_style=profile.content.intro_hook_style,
            visual_style=profile.video.caption_style,
            caption_style=profile.video.caption_style,
            music_genre=profile.music.genre,
            available_templates=template_names,
        )

        if not upload:
            initial_message += "\n\nIMPORTANT: Do NOT upload to YouTube. Skip the upload step."

        if budget_limit is not None:
            initial_message += (
                f"\n\nBUDGET CONSTRAINT: Total spend must stay under ${budget_limit:.2f}. "
                "Check remaining budget before expensive operations."
            )

        logger.info(
            "Agent starting video creation: topic=%r, video_id=%s",
            topic, video_id,
        )

        # Run the agent loop
        ctx = self._run_agent_loop(initial_message, ctx, budget_limit=budget_limit)

        # Save final context
        try:
            ctx.save()
        except Exception:
            logger.warning("Failed to save final pipeline context", exc_info=True)

        logger.info(
            "Agent completed video creation: video_id=%s, cost=$%.4f",
            video_id,
            getattr(self, "_toolkit", None) and self._toolkit.total_cost or 0,
        )

        return ctx

    def plan_video(
        self,
        topic: str,
        channel_profile: ChannelProfile | None = None,
    ) -> str:
        """Generate a production plan without executing it.

        Returns:
            The agent's production plan as a string.
        """
        profile = channel_profile or get_default_profile()

        try:
            from aividio.captions.templates import list_templates
            template_names = ", ".join(t["name"] for t in list_templates()[:20])
        except Exception:
            template_names = "bold_centered, hormozi, mrbeast, finance_serious, tech_modern"

        plan_prompt = PRODUCTION_PLAN_PROMPT.format(
            topic=topic,
            channel_name=profile.name,
            niche=profile.niche,
            target_audience=profile.target_audience,
            tone=profile.content.tone,
            target_duration="10-12 minutes",
            format="landscape",
            budget_limit="No limit",
            script_style=profile.content.script_style,
            hook_style=profile.content.intro_hook_style,
            visual_style=profile.video.caption_style,
            caption_style=profile.video.caption_style,
            music_genre=profile.music.genre,
            available_templates=template_names,
        )

        plan_prompt += (
            "\n\nIMPORTANT: Only create the production plan. "
            "Do NOT execute any tools. Just explain the plan step by step."
        )

        response = self.client.messages.create(
            model=AGENT_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": plan_prompt}],
        )

        return response.content[0].text

    def review_video(self, ctx: PipelineContext) -> str:
        """AI reviews an existing video and suggests improvements.

        Args:
            ctx: Pipeline context of the video to review.

        Returns:
            Review text with quality score and recommendations.
        """
        if ctx.script is None:
            return "Cannot review: no script found in context."

        effects_applied = ", ".join(ctx.completed_stages) if ctx.completed_stages else "None"

        review_prompt = REVIEW_PROMPT.format(
            title=ctx.script.get("title", "Unknown"),
            duration=f"{ctx.voiceover_duration:.0f}s" if ctx.voiceover_duration else "Unknown",
            section_count=len(ctx.script.get("sections", [])),
            effects=effects_applied,
            total_cost="Unknown",
        )

        response = self.client.messages.create(
            model=AGENT_MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": review_prompt}],
        )

        return response.content[0].text

    # ------------------------------------------------------------------
    # Core agent loop
    # ------------------------------------------------------------------

    def _run_agent_loop(
        self,
        initial_message: str,
        ctx: PipelineContext,
        budget_limit: float | None = None,
    ) -> PipelineContext:
        """Core agent loop -- Claude thinks, calls tools, we execute, repeat.

        The loop continues until Claude sends a response without any tool_use
        blocks (signalling completion) or we hit the max iteration count.
        """
        # Initialise the toolkit for this run
        self._toolkit = AgentToolkit(
            settings=self.settings,
            profile=ctx.channel_profile,
            ctx=ctx,
        )

        # Start the conversation
        self.conversation_history = [
            {"role": "user", "content": initial_message},
        ]

        for iteration in range(1, MAX_AGENT_ITERATIONS + 1):
            logger.info("Agent iteration %d/%d", iteration, MAX_AGENT_ITERATIONS)

            # Check budget before each iteration
            if budget_limit is not None and self._toolkit.total_cost >= budget_limit:
                logger.warning(
                    "Budget limit reached ($%.4f >= $%.4f). Stopping agent.",
                    self._toolkit.total_cost, budget_limit,
                )
                # Tell the agent the budget is exhausted
                self.conversation_history.append({
                    "role": "user",
                    "content": (
                        f"BUDGET EXHAUSTED: You have spent ${self._toolkit.total_cost:.4f} "
                        f"which meets or exceeds the limit of ${budget_limit:.2f}. "
                        "Please wrap up with what you have and provide a summary."
                    ),
                })

            # Call Claude
            try:
                response = self.client.messages.create(
                    model=AGENT_MODEL,
                    max_tokens=8192,
                    system=SYSTEM_PROMPT,
                    tools=self.tools,
                    messages=self.conversation_history,
                )
            except anthropic.APIError as exc:
                logger.error("Claude API error: %s", exc)
                # Wait and retry once
                import time
                time.sleep(2)
                try:
                    response = self.client.messages.create(
                        model=AGENT_MODEL,
                        max_tokens=8192,
                        system=SYSTEM_PROMPT,
                        tools=self.tools,
                        messages=self.conversation_history,
                    )
                except anthropic.APIError as exc2:
                    logger.error("Claude API retry failed: %s", exc2)
                    break

            # Process response content blocks
            assistant_content: list[dict[str, Any]] = []
            tool_calls: list[dict[str, Any]] = []

            for block in response.content:
                if block.type == "text":
                    assistant_content.append({
                        "type": "text",
                        "text": block.text,
                    })
                    logger.info("Agent: %s", block.text[:200])
                elif block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
                    tool_calls.append({
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

            # Add the full assistant message to history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_content,
            })

            # If no tool calls, the agent is done
            if response.stop_reason == "end_turn" and not tool_calls:
                logger.info("Agent signalled completion (no tool calls).")
                break

            if not tool_calls:
                logger.info("Agent response has no tool calls. Finishing.")
                break

            # Execute tool calls and build tool_result messages
            tool_results: list[dict[str, Any]] = []
            for tc in tool_calls:
                tool_name = tc["name"]
                tool_input = tc["input"]
                tool_id = tc["id"]

                logger.info("Executing tool: %s(%s)", tool_name, json.dumps(tool_input)[:200])

                # Notify callback
                if self._step_callback:
                    try:
                        self._step_callback(tool_name, json.dumps(tool_input)[:200])
                    except Exception:
                        pass

                result_str = self._toolkit.execute(tool_name, tool_input)

                logger.info("Tool result (%s): %s", tool_name, result_str[:300])

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": result_str,
                })

                # Mark completed stage
                ctx.completed_stages.append(tool_name)

            # Add tool results back to the conversation
            self.conversation_history.append({
                "role": "user",
                "content": tool_results,
            })

            # Save context after each tool execution batch
            try:
                ctx.save()
            except Exception:
                logger.warning("Failed to save context at iteration %d", iteration, exc_info=True)

        else:
            logger.warning("Agent hit max iterations (%d). Stopping.", MAX_AGENT_ITERATIONS)

        return ctx

    # ------------------------------------------------------------------
    # Tool definitions for Claude
    # ------------------------------------------------------------------

    def _build_tool_definitions(self) -> list[dict[str, Any]]:
        """Build Claude tool definitions with JSON Schema for all capabilities."""
        return [
            {
                "name": "generate_script",
                "description": (
                    "Generate a complete video script with hook, sections (each with narration, "
                    "visual queries, timing), and outro. The script drives the entire pipeline."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "The video topic or prompt to generate a script for.",
                        },
                        "style": {
                            "type": "string",
                            "description": "Script style: 'listicle', 'explainer', 'story', 'tutorial', 'comparison'.",
                            "enum": ["listicle", "explainer", "story", "tutorial", "comparison"],
                            "default": "listicle",
                        },
                        "target_duration_minutes": {
                            "type": "integer",
                            "description": "Target video duration in minutes.",
                            "default": 10,
                        },
                    },
                    "required": ["topic"],
                },
            },
            {
                "name": "generate_voiceover",
                "description": (
                    "Convert the script narration into speech audio using a TTS provider. "
                    "ElevenLabs offers the most natural voices; OpenAI is cheaper."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "description": "TTS provider to use.",
                            "enum": ["elevenlabs", "openai", "replicate", "fal"],
                            "default": "elevenlabs",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "transcribe_audio",
                "description": (
                    "Run Whisper on the voiceover audio to get word-level timestamps. "
                    "Required for captions, zoom effects, B-roll, and clip extraction."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            {
                "name": "search_stock_media",
                "description": (
                    "Search and download stock videos/images from Pexels or Pixabay. "
                    "Use query='__all_sections__' to auto-source media for ALL script sections."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "Search query for stock media, or '__all_sections__' to "
                                "auto-source for all script sections."
                            ),
                        },
                        "media_type": {
                            "type": "string",
                            "description": "Type of media to search for.",
                            "enum": ["video", "image"],
                            "default": "video",
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of results to download.",
                            "default": 3,
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "generate_ai_video",
                "description": (
                    "Generate an AI video clip using models like Kling 2.1, Runway Gen-3, "
                    "MiniMax, or Hunyuan via Replicate/fal. The ModelOrchestrator auto-selects "
                    "the best model if 'auto' is specified."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "Visual description of the video clip to generate.",
                        },
                        "model": {
                            "type": "string",
                            "description": (
                                "Model to use: 'auto' (smart routing), 'kling-2.1', "
                                "'runway-gen3', 'minimax-video-01', 'hunyuan-video', 'luma-ray', 'wan2.1'."
                            ),
                            "default": "auto",
                        },
                        "duration": {
                            "type": "number",
                            "description": "Clip duration in seconds.",
                            "default": 5.0,
                        },
                        "section_index": {
                            "type": "integer",
                            "description": "Which script section this clip belongs to.",
                            "default": 0,
                        },
                    },
                    "required": ["prompt"],
                },
            },
            {
                "name": "generate_ai_image",
                "description": (
                    "Generate an AI image using DALL-E, Flux (Replicate), or Stable Diffusion (fal)."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "Description of the image to generate.",
                        },
                        "provider": {
                            "type": "string",
                            "description": "Image generation provider.",
                            "enum": ["dalle", "replicate", "fal"],
                            "default": "dalle",
                        },
                        "section_index": {
                            "type": "integer",
                            "description": "Which script section this image belongs to.",
                            "default": 0,
                        },
                    },
                    "required": ["prompt"],
                },
            },
            {
                "name": "assemble_video",
                "description": (
                    "Assemble voiceover audio, media clips, and optional music into the final "
                    "video using FFmpeg. Handles clip fitting, transitions, and timing."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            {
                "name": "apply_captions",
                "description": (
                    "Add animated word-level captions to the video. 41+ template styles available. "
                    "Use 'auto' to auto-select based on channel niche."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "template": {
                            "type": "string",
                            "description": (
                                "Caption template name or 'auto' for niche-based selection. "
                                "Examples: hormozi, mrbeast, bold_centered, finance_serious, "
                                "tech_modern, motivation_fire, education_clear, gaming_hype."
                            ),
                            "default": "auto",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "apply_magic_zoom",
                "description": (
                    "Add auto-zoom effects at emphasis points (statistics, emotional peaks, "
                    "rhetorical questions). Uses Claude to detect the best zoom moments."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "style": {
                            "type": "string",
                            "description": "Zoom style.",
                            "enum": ["smooth", "crash", "expo", "linear"],
                            "default": "smooth",
                        },
                        "max_zooms": {
                            "type": "integer",
                            "description": "Maximum number of zoom effects.",
                            "default": 8,
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "remove_silence",
                "description": (
                    "Remove dead air, long pauses, and filler words (um, uh, like, etc.) "
                    "to tighten pacing and improve viewer retention."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "mode": {
                            "type": "string",
                            "description": (
                                "Aggressiveness: 'normal' (>=800ms pauses), "
                                "'fast' (>=500ms), 'extra_fast' (>=300ms)."
                            ),
                            "enum": ["normal", "fast", "extra_fast"],
                            "default": "normal",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "add_broll",
                "description": (
                    "Analyse the transcript and insert contextual B-roll footage at moments "
                    "where it would enhance the viewer experience. Sources from Pexels/Pixabay."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "max_clips": {
                            "type": "integer",
                            "description": "Maximum number of B-roll clips to insert.",
                            "default": 6,
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "add_emoji_sfx",
                "description": (
                    "Add emoji overlays at keyword moments and sound effects at emphasis points. "
                    "Uses AI for context-aware SFX placement."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            {
                "name": "generate_thumbnail",
                "description": (
                    "Generate a YouTube thumbnail image using AI image generation. "
                    "Optimised for CTR with bold visuals."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "style": {
                            "type": "string",
                            "description": "Thumbnail style or 'auto' for profile defaults.",
                            "default": "auto",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "optimize_seo",
                "description": (
                    "Optimise the video title, description, and tags for YouTube SEO. "
                    "Generates multiple title options ranked by estimated CTR."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            {
                "name": "apply_brand_kit",
                "description": (
                    "Apply channel branding: logo overlay, watermark, intro/outro sequences."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            {
                "name": "export_platforms",
                "description": (
                    "Export the video for multiple platforms (YouTube, TikTok, Instagram) "
                    "with platform-specific formatting, cropping, and re-encoding."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "platforms": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Platforms to export for: youtube, tiktok, instagram_reels, "
                                "instagram_feed, youtube_shorts."
                            ),
                            "default": ["youtube"],
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "extract_clips",
                "description": (
                    "Extract viral short-form clips from the long-form video for TikTok, "
                    "Shorts, and Reels. Uses Claude to identify the most clip-worthy segments."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "count": {
                            "type": "integer",
                            "description": "Number of clips to extract.",
                            "default": 3,
                        },
                        "format": {
                            "type": "string",
                            "description": "Output format for clips.",
                            "enum": ["portrait", "landscape", "square"],
                            "default": "portrait",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "upload_youtube",
                "description": (
                    "Upload the finished video to YouTube with title, description, tags, "
                    "thumbnail, and visibility settings."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "visibility": {
                            "type": "string",
                            "description": "YouTube visibility setting.",
                            "enum": ["public", "unlisted", "private"],
                            "default": "private",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "estimate_cost",
                "description": (
                    "Estimate the cost of planned production steps before executing them. "
                    "Shows per-service breakdown and total."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "steps": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of step names to estimate cost for.",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "track_usage",
                "description": "Manually log an API usage event with service name, operation, and cost.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Service name (e.g. 'claude', 'elevenlabs').",
                        },
                        "operation": {
                            "type": "string",
                            "description": "Operation name (e.g. 'script_generation').",
                        },
                        "cost": {
                            "type": "number",
                            "description": "Cost in USD.",
                        },
                    },
                    "required": ["service", "operation", "cost"],
                },
            },
        ]
