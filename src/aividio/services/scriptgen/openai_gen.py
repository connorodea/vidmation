"""OpenAI GPT-4o script generator implementation (fallback)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import openai

from aividio.config.profiles import ChannelProfile
from aividio.services.scriptgen.base import SCRIPT_SCHEMA, ScriptGenerator
from aividio.utils.retry import retry

if TYPE_CHECKING:
    from aividio.config.settings import Settings

_SYSTEM_PROMPT = """\
You are a professional YouTube scriptwriter specialising in faceless \
channel content.  Return **only** valid JSON matching the schema below — \
no markdown fences, no extra text.

JSON Schema:
{schema}

Rules:
- The "hook" should grab attention in the first 5 seconds.
- Each section's "narration" should be conversational and paced for \
  voice-over (~150 words/min).
- "visual_query" must be a concise, search-friendly phrase for stock \
  media search or AI image generation.
- "visual_type": one of stock_video, stock_image, ai_image.
- "estimated_duration_seconds" per section reflects narration length.
- "total_estimated_duration_seconds" = sum of section durations.
- "tags": 8-15 relevant YouTube tags.
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


class OpenAIScriptGenerator(ScriptGenerator):
    """Generate scripts using OpenAI's GPT-4o API."""

    MODEL = "gpt-4o"
    MAX_TOKENS = 4096

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__(settings=settings)
        api_key = self.settings.openai_api_key.get_secret_value()
        if not api_key:
            raise ValueError(
                "openai_api_key is not configured. "
                "Set VIDMATION_OPENAI_API_KEY in your environment."
            )
        self._client = openai.OpenAI(api_key=api_key)

    @retry(max_attempts=3, base_delay=2.0, exceptions=(openai.APIError,))
    def generate(self, topic: str, profile: ChannelProfile) -> dict:
        """Call GPT-4o to produce a structured video script."""
        self.logger.info("Generating script for topic=%r via OpenAI GPT-4o", topic)

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

        response = self._client.chat.completions.create(
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
        )

        raw_text = response.choices[0].message.content or ""
        raw_text = raw_text.strip()

        try:
            script: dict = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            self.logger.error("OpenAI returned invalid JSON: %s", exc)
            raise ValueError("OpenAI response was not valid JSON") from exc

        self.logger.info(
            "Script generated: %r (%d sections, ~%ds)",
            script.get("title", "untitled"),
            len(script.get("sections", [])),
            script.get("total_estimated_duration_seconds", 0),
        )
        return script
