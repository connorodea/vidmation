"""Abstract base class for script generators."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from aividio.config.profiles import ChannelProfile
from aividio.services.base import BaseService

# Canonical JSON schema that every generator must return.
SCRIPT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "title",
        "description",
        "tags",
        "hook",
        "sections",
        "outro",
        "total_estimated_duration_seconds",
    ],
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "hook": {"type": "string"},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "section_number",
                    "heading",
                    "narration",
                    "visual_query",
                    "visual_type",
                    "estimated_duration_seconds",
                ],
                "properties": {
                    "section_number": {"type": "integer"},
                    "heading": {"type": "string"},
                    "narration": {"type": "string"},
                    "visual_query": {"type": "string"},
                    "visual_type": {
                        "type": "string",
                        "enum": ["stock_video", "stock_image", "ai_image"],
                    },
                    "estimated_duration_seconds": {"type": "number"},
                },
            },
        },
        "outro": {"type": "string"},
        "total_estimated_duration_seconds": {"type": "number"},
    },
}


class ScriptGenerator(BaseService):
    """ABC for LLM-backed YouTube video script generators."""

    @abstractmethod
    def generate(self, topic: str, profile: ChannelProfile) -> dict:
        """Generate a structured video script.

        Args:
            topic: The video topic / title idea.
            profile: Channel profile controlling tone, style, niche, etc.

        Returns:
            A dict matching :data:`SCRIPT_SCHEMA`.
        """
        ...
