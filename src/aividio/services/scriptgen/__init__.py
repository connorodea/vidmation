"""Script generation service — LLM-powered YouTube script creation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aividio.config.settings import get_settings
from aividio.services.scriptgen.base import ScriptGenerator

if TYPE_CHECKING:
    from aividio.config.settings import Settings

__all__ = ["ScriptGenerator", "create_script_generator"]


def create_script_generator(
    provider: str | None = None,
    settings: Settings | None = None,
) -> ScriptGenerator:
    """Factory: return a ScriptGenerator for the requested provider.

    Args:
        provider: ``"claude"`` or ``"openai"``.  Falls back to
            ``settings.default_llm_provider`` when *None*.
        settings: Optional settings override.
    """
    settings = settings or get_settings()
    provider = provider or settings.default_llm_provider

    if provider == "claude":
        from aividio.services.scriptgen.claude import ClaudeScriptGenerator

        return ClaudeScriptGenerator(settings=settings)

    if provider == "openai":
        from aividio.services.scriptgen.openai_gen import OpenAIScriptGenerator

        return OpenAIScriptGenerator(settings=settings)

    raise ValueError(f"Unknown script-generation provider: {provider!r}")
