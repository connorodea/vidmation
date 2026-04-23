"""Prompt pack generator — structured prompt bundles for downstream AI systems."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import anthropic

from aividio.config.profiles import ChannelProfile
from aividio.services.base import BaseService
from aividio.utils.retry import retry

if TYPE_CHECKING:
    from aividio.config.settings import Settings

logger = logging.getLogger(__name__)

_PROMPT_PACK_SYSTEM = """\
You are an AI content strategist that creates comprehensive prompt packs for \
video production pipelines.  Given a topic, channel profile, and video script, \
produce a structured prompt pack in **strict JSON** — no markdown fences, no \
commentary outside the JSON object.

The prompt pack must contain all the context that downstream AI systems \
(image generators, SEO tools, thumbnail generators, TTS, music selectors) need \
to produce cohesive, on-brand content.

Return JSON matching this structure exactly:
{
  "channel_positioning": {
    "niche": "<channel niche>",
    "audience": "<target audience description>",
    "tone": "<voice and tone>",
    "visual_style": "<overall visual aesthetic>",
    "brand_keywords": ["<key brand terms>"]
  },
  "video_brief": {
    "title": "<optimized title>",
    "topic": "<core topic>",
    "angle": "<unique angle or perspective>",
    "keywords": ["<primary SEO keywords>"],
    "evidence_points": ["<key facts, stats, or claims used>"],
    "target_duration_seconds": <int>,
    "content_type": "<listicle|explainer|story|comparison|tutorial|opinion>"
  },
  "generation_rules": {
    "script_structure": "<structure pattern used>",
    "retention_targets": {
      "hook_seconds": 5,
      "pattern_interrupt_interval_seconds": 35,
      "min_curiosity_gaps": 3,
      "cta_placement": "<mid-video and/or outro>"
    },
    "thumbnail_style": "<recommended thumbnail approach>",
    "caption_style": "<bold_centered|minimal|dynamic>",
    "music_mood": "<recommended background music mood>"
  },
  "visual_prompts": [
    {
      "section_number": <int>,
      "heading": "<section heading>",
      "image_prompt": "<detailed AI image generation prompt>",
      "video_search_query": "<stock video search query>",
      "visual_type": "stock_video|stock_image|ai_image",
      "mood": "<visual mood for this section>",
      "color_palette": "<suggested dominant colors>"
    }
  ],
  "seo_payload": {
    "youtube": {
      "title": "<YouTube-optimized title>",
      "description": "<full YouTube description with links and timestamps>",
      "tags": ["<YouTube tags>"],
      "hashtags": ["<3-5 hashtags>"]
    },
    "tiktok": {
      "caption": "<TikTok caption with hashtags>",
      "hashtags": ["<TikTok hashtags>"]
    },
    "instagram": {
      "caption": "<Instagram Reels caption>",
      "hashtags": ["<Instagram hashtags>"]
    }
  }
}
"""


class PromptPackGenerator(BaseService):
    """Generate comprehensive prompt packs for downstream AI systems.

    A prompt pack bundles all the context that image generators, SEO tools,
    thumbnail generators, TTS engines, and music selectors need to produce
    cohesive, on-brand video content from a single source of truth.
    """

    MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 8192

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__(settings=settings)
        api_key = self.settings.anthropic_api_key.get_secret_value()
        if not api_key:
            raise ValueError(
                "anthropic_api_key is not configured. "
                "Set AIVIDIO_ANTHROPIC_API_KEY in your environment."
            )
        self._client = anthropic.Anthropic(api_key=api_key)

    @retry(max_attempts=3, base_delay=2.0, exceptions=(anthropic.APIError,))
    def generate(
        self,
        topic: str,
        channel: ChannelProfile,
        script: dict,
    ) -> dict[str, Any]:
        """Create a full prompt pack for video production.

        Args:
            topic: The video topic / prompt.
            channel: Channel profile with tone, niche, audience, and style.
            script: The generated video script dict.

        Returns:
            A prompt pack dict containing channel_positioning, video_brief,
            generation_rules, visual_prompts, and seo_payload.
        """
        self.logger.info(
            "Generating prompt pack for topic=%r, channel=%r",
            topic,
            channel.name,
        )

        user_message = (
            f"Generate a comprehensive prompt pack for this video:\n\n"
            f"**Topic:** {topic}\n\n"
            f"**Channel Profile:**\n"
            f"- Name: {channel.name}\n"
            f"- Niche: {channel.niche}\n"
            f"- Target audience: {channel.target_audience}\n"
            f"- Tone: {channel.content.tone}\n"
            f"- Script style: {channel.content.script_style}\n"
            f"- Hook style: {channel.content.intro_hook_style}\n"
            f"- CTA style: {channel.content.cta_style}\n"
            f"- Video format: {channel.video.format}\n"
            f"- Thumbnail style: {channel.thumbnail.style}\n"
            f"- Music genre: {channel.music.genre}\n"
            f"- Caption style: {channel.video.caption_style}\n\n"
            f"**Script:**\n{json.dumps(script, indent=2)}"
        )

        response = self._client.messages.create(
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS,
            system=_PROMPT_PACK_SYSTEM,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text.strip()

        # Strip markdown code fences if the model wraps them.
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]

        try:
            prompt_pack: dict = json.loads(raw.strip())
        except json.JSONDecodeError as exc:
            self.logger.error("Claude returned invalid JSON for prompt pack: %s", exc)
            raise ValueError("Prompt pack response was not valid JSON") from exc

        # Validate expected top-level keys.
        expected_keys = {
            "channel_positioning",
            "video_brief",
            "generation_rules",
            "visual_prompts",
            "seo_payload",
        }
        missing = expected_keys - set(prompt_pack.keys())
        if missing:
            self.logger.warning(
                "Prompt pack is missing expected keys: %s", missing
            )

        self.logger.info(
            "Prompt pack generated: %d visual prompts, %d SEO platforms",
            len(prompt_pack.get("visual_prompts", [])),
            len(prompt_pack.get("seo_payload", {})),
        )
        return prompt_pack

    def generate_minimal(
        self,
        topic: str,
        channel: ChannelProfile,
    ) -> dict[str, Any]:
        """Generate a lightweight prompt pack without a script.

        Useful for pre-production planning before script generation.

        Args:
            topic: The video topic.
            channel: The channel profile.

        Returns:
            A partial prompt pack with channel_positioning, video_brief,
            and generation_rules (no visual_prompts since there is no script).
        """
        self.logger.info(
            "Generating minimal prompt pack for topic=%r", topic
        )

        # Build a placeholder script structure so the prompt still works.
        placeholder_script = {
            "title": topic,
            "description": f"A video about {topic}",
            "tags": [],
            "hook": "",
            "sections": [],
            "outro": "",
            "total_estimated_duration_seconds": 0,
        }

        return self.generate(
            topic=topic,
            channel=channel,
            script=placeholder_script,
        )
