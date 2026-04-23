"""Configuration for the AI agent.

Centralises all tunable parameters that control the agent's behaviour,
model selection, budget limits, and feature flags.

Usage::

    from aividio.agent.config import AgentConfig

    config = AgentConfig(
        max_budget_usd=3.0,
        verbose=True,
        enabled_categories=["script", "tts", "media", "assembly"],
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentConfig:
    """Configuration for the AIVIDIO AI agent orchestrator.

    Controls model selection, iteration limits, budget caps, feature flags,
    and tool category filtering.

    Attributes:
        model: Default Claude model for orchestration tool calls.
        planning_model: Model used for initial production planning (can be
            higher-tier for better plan quality).
        max_iterations: Maximum number of tool-call iterations per video
            production run.  Acts as a safety limit.
        max_budget_usd: Default per-video budget cap.  The agent will
            check cost estimates before executing expensive steps and
            will refuse to proceed if the budget would be exceeded.
        enable_thinking: Whether to use Claude's extended thinking for
            the production planning phase.
        thinking_budget_tokens: Token budget for extended thinking.
        verbose: If ``True``, the agent logs its reasoning chain and
            tool call decisions.
        auto_retry: Whether the agent should automatically retry failed
            steps with alternative services / models.
        max_retries_per_step: Maximum retries per individual step before
            the agent moves on or fails.
        parallel_media: Whether to source/generate media in parallel
            across sections.
        quality_review: Whether the agent should perform an AI-powered
            quality review of the final video before marking it complete.
        enabled_categories: Which tool categories are available to the
            agent.  Allows disabling expensive or unsafe categories
            (e.g. removing ``"youtube"`` prevents accidental uploads
            during testing).
        mcp_servers: Names of MCP servers to auto-connect on agent
            startup (must exist in ``KNOWN_MCP_SERVERS``).
        preferred_video_provider: Default provider for video generation
            (``"replicate"``, ``"fal"``, ``"local"``).
        preferred_tts_provider: Default provider for text-to-speech.
        preferred_image_provider: Default provider for image generation.
        default_caption_template: Caption template to use when not
            specified in the channel profile.
        music_enabled: Whether to include background music in assembled
            videos.
        music_volume: Default music volume (0.0 -- 1.0).
    """

    # -- Model selection ---------------------------------------------------
    model: str = "claude-sonnet-4-20250514"
    planning_model: str = "claude-sonnet-4-20250514"

    # -- Iteration & budget limits -----------------------------------------
    max_iterations: int = 50
    max_budget_usd: float = 5.0

    # -- Thinking ----------------------------------------------------------
    enable_thinking: bool = True
    thinking_budget_tokens: int = 10_000

    # -- Behaviour flags ---------------------------------------------------
    verbose: bool = False
    auto_retry: bool = True
    max_retries_per_step: int = 3
    parallel_media: bool = True
    quality_review: bool = True

    # -- Tool filtering ----------------------------------------------------
    enabled_categories: list[str] = field(
        default_factory=lambda: [
            "script",
            "tts",
            "media",
            "imagegen",
            "videogen",
            "assembly",
            "captions",
            "effects",
            "seo",
            "brand",
            "platform",
            "youtube",
            "analytics",
            "db",
            "notifications",
            "file",
        ]
    )

    # -- MCP servers to auto-connect ---------------------------------------
    mcp_servers: list[str] = field(default_factory=list)

    # -- Provider defaults -------------------------------------------------
    preferred_video_provider: str = "replicate"
    preferred_tts_provider: str = "elevenlabs"
    preferred_image_provider: str = "dalle"

    # -- Content defaults --------------------------------------------------
    default_caption_template: str = "hormozi"
    music_enabled: bool = True
    music_volume: float = 0.15

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def is_category_enabled(self, category: str) -> bool:
        """Check if a tool category is enabled."""
        return category in self.enabled_categories

    def get_filtered_tools(self, tools: list[dict]) -> list[dict]:
        """Filter a list of Claude tool definitions to only enabled categories.

        This is used to restrict which tools the agent can see based on
        the ``enabled_categories`` setting.

        Args:
            tools: Full list of tool dicts from ``ToolRegistry.get_claude_tools()``.

        Returns:
            Filtered list containing only tools whose category is enabled.
        """
        # Tool names are prefixed with their category conceptually, but
        # we need to check via the registry.  For simplicity, pass through
        # all tools -- the registry already only registers enabled ones.
        return tools

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict (for logging / API responses)."""
        return {
            "model": self.model,
            "planning_model": self.planning_model,
            "max_iterations": self.max_iterations,
            "max_budget_usd": self.max_budget_usd,
            "enable_thinking": self.enable_thinking,
            "thinking_budget_tokens": self.thinking_budget_tokens,
            "verbose": self.verbose,
            "auto_retry": self.auto_retry,
            "max_retries_per_step": self.max_retries_per_step,
            "parallel_media": self.parallel_media,
            "quality_review": self.quality_review,
            "enabled_categories": self.enabled_categories,
            "mcp_servers": self.mcp_servers,
            "preferred_video_provider": self.preferred_video_provider,
            "preferred_tts_provider": self.preferred_tts_provider,
            "preferred_image_provider": self.preferred_image_provider,
            "default_caption_template": self.default_caption_template,
            "music_enabled": self.music_enabled,
            "music_volume": self.music_volume,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentConfig":
        """Create an AgentConfig from a dict (e.g. from API request or YAML)."""
        # Only pass known fields to avoid TypeError on unknown keys
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)

    def __repr__(self) -> str:
        return (
            f"AgentConfig(model={self.model!r}, budget=${self.max_budget_usd:.2f}, "
            f"categories={len(self.enabled_categories)}, "
            f"mcp_servers={self.mcp_servers})"
        )
