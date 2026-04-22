"""Claude (Anthropic) script generator implementation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import anthropic

from aividio.config.profiles import ChannelProfile
from aividio.services.scriptgen.base import SCRIPT_SCHEMA, ScriptGenerator
from aividio.utils.retry import retry

if TYPE_CHECKING:
    from aividio.config.settings import Settings

_SYSTEM_PROMPT = """\
You are a professional YouTube scriptwriter specialising in faceless \
channel content.  You produce scripts in **strict JSON** matching the \
schema below — no markdown fences, no commentary outside the JSON object.

JSON Schema:
{schema}

Guidelines:
- The "hook" should grab attention in the first 5 seconds.
- Each section's "narration" should be conversational and paced for \
  voice-over (roughly 150 words per minute).
- "visual_query" must be a concise, search-friendly phrase suitable for \
  stock-media search or AI image generation.
- "visual_type" must be one of: stock_video, stock_image, ai_image.
- "estimated_duration_seconds" per section should reflect narration length.
- "total_estimated_duration_seconds" is the sum of all section durations.
- "tags" should include 8-15 relevant YouTube tags.
"""

_USER_TEMPLATE = """\
Create a YouTube video script about: **{topic}**

Channel profile:
- Niche: {niche}
- Tone: {tone}
- Script style: {script_style}
- Hook style: {hook_style}
- CTA style: {cta_style}
- Typical topics: {typical_topics}
- Target audience: {target_audience}
"""


class ClaudeScriptGenerator(ScriptGenerator):
    """Generate scripts using Anthropic's Claude API."""

    MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 4096

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__(settings=settings)
        api_key = self.settings.anthropic_api_key.get_secret_value()
        if not api_key:
            raise ValueError(
                "anthropic_api_key is not configured. "
                "Set VIDMATION_ANTHROPIC_API_KEY in your environment."
            )
        self._client = anthropic.Anthropic(api_key=api_key)

    @retry(max_attempts=3, base_delay=2.0, exceptions=(anthropic.APIError,))
    def generate(self, topic: str, profile: ChannelProfile) -> dict:
        """Call Claude to produce a structured video script."""
        self.logger.info("Generating script for topic=%r via Claude", topic)

        system = _SYSTEM_PROMPT.format(schema=json.dumps(SCRIPT_SCHEMA, indent=2))

        user_msg = _USER_TEMPLATE.format(
            topic=topic,
            niche=profile.niche,
            tone=profile.content.tone,
            script_style=profile.content.script_style,
            hook_style=profile.content.intro_hook_style,
            cta_style=profile.content.cta_style,
            typical_topics=", ".join(profile.content.typical_topics) or "general",
            target_audience=profile.target_audience,
        )

        response = self._client.messages.create(
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )

        raw_text = response.content[0].text.strip()

        # Strip markdown code fences if the model wraps them anyway.
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1]
        if raw_text.endswith("```"):
            raw_text = raw_text.rsplit("```", 1)[0]

        try:
            script: dict = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            self.logger.error("Claude returned invalid JSON: %s", exc)
            raise ValueError("Claude response was not valid JSON") from exc

        self.logger.info(
            "Script generated: %r (%d sections, ~%ds)",
            script.get("title", "untitled"),
            len(script.get("sections", [])),
            script.get("total_estimated_duration_seconds", 0),
        )
        return script
