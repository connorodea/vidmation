"""AI-powered content repurposer — generates social media content from YouTube scripts."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import openai

from aividio.config.profiles import ChannelProfile
from aividio.services.base import BaseService
from aividio.utils.retry import retry

if TYPE_CHECKING:
    from aividio.config.settings import Settings

# All supported platform keys.
ALL_PLATFORMS: list[str] = [
    "instagram_reels",
    "tiktok",
    "instagram_feed",
    "facebook_video",
    "x_thread",
    "x_single",
]

# ── JSON schema the LLM must conform to ─────────────────────────────────────

_CLIP_SUGGESTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["start_sec", "end_sec", "reason"],
    "properties": {
        "start_sec": {"type": "number"},
        "end_sec": {"type": "number"},
        "reason": {"type": "string"},
    },
}

_CAROUSEL_SLIDE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["slide_number", "text"],
    "properties": {
        "slide_number": {"type": "integer"},
        "text": {"type": "string"},
    },
}

REPURPOSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "instagram_reels": {
            "type": "object",
            "required": [
                "hook",
                "caption",
                "hashtags",
                "clip_suggestions",
                "music_suggestion",
            ],
            "properties": {
                "hook": {"type": "string", "description": "First 3 seconds text overlay"},
                "caption": {
                    "type": "string",
                    "maxLength": 2200,
                    "description": "Instagram caption (max 2200 chars)",
                },
                "hashtags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 20,
                    "maxItems": 30,
                },
                "clip_suggestions": {
                    "type": "array",
                    "items": _CLIP_SUGGESTION_SCHEMA,
                    "minItems": 3,
                    "maxItems": 5,
                    "description": "Best 3-5 short clips (15-60s each)",
                },
                "music_suggestion": {
                    "type": "string",
                    "description": "Trending audio genre/mood recommendation",
                },
            },
        },
        "tiktok": {
            "type": "object",
            "required": [
                "hook",
                "caption",
                "hashtags",
                "clip_suggestions",
                "music_suggestion",
            ],
            "properties": {
                "hook": {"type": "string", "description": "First 3 seconds text overlay"},
                "caption": {
                    "type": "string",
                    "maxLength": 4000,
                    "description": "TikTok caption (max 4000 chars)",
                },
                "hashtags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 20,
                    "maxItems": 30,
                },
                "clip_suggestions": {
                    "type": "array",
                    "items": _CLIP_SUGGESTION_SCHEMA,
                    "minItems": 3,
                    "maxItems": 5,
                    "description": "Best 3-5 short clips (15-60s each)",
                },
                "music_suggestion": {
                    "type": "string",
                    "description": "Trending audio genre/mood recommendation",
                },
            },
        },
        "instagram_feed": {
            "type": "object",
            "required": ["caption", "hashtags", "carousel_slides", "alt_text"],
            "properties": {
                "caption": {
                    "type": "string",
                    "description": "Engaging caption with CTA",
                },
                "hashtags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 20,
                    "maxItems": 30,
                },
                "carousel_slides": {
                    "type": "array",
                    "items": _CAROUSEL_SLIDE_SCHEMA,
                    "minItems": 5,
                    "maxItems": 10,
                    "description": "Text slides summarising the video for a carousel post",
                },
                "alt_text": {
                    "type": "string",
                    "description": "Accessibility alt-text for the post image",
                },
            },
        },
        "facebook_video": {
            "type": "object",
            "required": ["title", "description", "clip_suggestions"],
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Attention-grabbing video title",
                },
                "description": {
                    "type": "string",
                    "description": "Conversational description, longer than YouTube",
                },
                "clip_suggestions": {
                    "type": "array",
                    "items": _CLIP_SUGGESTION_SCHEMA,
                    "minItems": 2,
                    "maxItems": 3,
                    "description": "Best 2-3 clips for Facebook (1-3 minutes each)",
                },
            },
        },
        "x_thread": {
            "type": "object",
            "required": ["tweets", "thread_hook", "hashtags"],
            "properties": {
                "tweets": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 280},
                    "minItems": 5,
                    "maxItems": 10,
                    "description": "Thread of 5-10 tweets, each <=280 chars",
                },
                "thread_hook": {
                    "type": "string",
                    "maxLength": 280,
                    "description": "First tweet — the most attention-grabbing",
                },
                "hashtags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 3,
                    "maxItems": 5,
                },
            },
        },
        "x_single": {
            "type": "object",
            "required": ["text", "hashtags"],
            "properties": {
                "text": {
                    "type": "string",
                    "maxLength": 280,
                    "description": "Punchy single tweet with hook (<=280 chars)",
                },
                "hashtags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2,
                    "maxItems": 3,
                },
            },
        },
    },
}

# ── Prompt templates ─────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a world-class social-media content strategist.  Given a YouTube video \
script you produce ready-to-publish content for every requested platform.

Return **only** valid JSON matching the schema below — no markdown fences, no \
extra commentary.

JSON Schema:
{schema}

Platform-specific best practices you MUST follow:
- **Instagram Reels**: lead with a 3-second hook text overlay; caption max \
  2 200 chars; use 20-30 niche-relevant hashtags mixing broad and niche; pick \
  clips that are visually dynamic (15-60 s); suggest a trending audio mood.
- **TikTok**: hook must be curiosity-driven (\"You won't believe…\" style); \
  caption max 4 000 chars; 20-30 hashtags; favour shorter clips (15-30 s); \
  suggest trending audio genre.
- **Instagram Feed / Carousel**: opening line should stop the scroll; include \
  CTA (save, share, comment); carousel slides should summarise the video with \
  one key insight per slide; alt-text for accessibility.
- **Facebook Video**: title should provoke curiosity or emotion; description \
  should be conversational and longer than YouTube's; clips should be 1-3 min \
  for watch-time optimisation.
- **X/Twitter Thread**: first tweet is the hook — make it irresistible; each \
  tweet ≤ 280 chars; 5-10 tweets forming a logical narrative; 3-5 hashtags; \
  end with a CTA.
- **X/Twitter Single**: punchy and self-contained ≤ 280 chars; 2-3 hashtags.

When generating clip_suggestions, use the section numbers / estimated \
durations from the script to approximate start_sec and end_sec timestamps.  \
Each clip should have a clear "reason" explaining why it works as a standalone \
short-form clip.

Hashtags should NOT include the '#' symbol — just the word/phrase.
"""

_USER_TEMPLATE = """\
Repurpose the following YouTube video script into social media content for \
these platforms: {platforms}

**Video title:** {title}
**Video description:** {description}
**Video hook:** {hook}
**Video outro:** {outro}
**Video tags:** {tags}

**Channel niche:** {niche}
**Channel tone:** {tone}
**Target audience:** {target_audience}

**Script sections:**
{sections_text}

Generate engaging, platform-optimised content for each requested platform.  \
Only include the platforms listed above in your JSON response.
"""


def _format_sections(sections: list[dict[str, Any]]) -> str:
    """Format script sections into a readable text block for the prompt."""
    parts: list[str] = []
    for sec in sections:
        num = sec.get("section_number", "?")
        heading = sec.get("heading", "")
        narration = sec.get("narration", "")
        duration = sec.get("estimated_duration_seconds", 0)
        parts.append(
            f"[Section {num}] {heading} (~{duration}s)\n{narration}"
        )
    return "\n\n".join(parts)


class ContentRepurposer(BaseService):
    """Generate social media content from a YouTube video script using GPT-4o.

    Usage::

        from aividio.services.repurpose import create_repurposer

        repurposer = create_repurposer()
        social_content = repurposer.generate(
            script=my_script_dict,
            channel_profile=my_profile,
            platforms=["instagram_reels", "tiktok", "x_thread"],
        )
    """

    MODEL = "gpt-4o"
    MAX_TOKENS = 8192

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__(settings=settings)
        api_key = self.settings.openai_api_key.get_secret_value()
        if not api_key:
            raise ValueError(
                "openai_api_key is not configured. "
                "Set AIVIDIO_OPENAI_API_KEY in your environment."
            )
        self._client = openai.OpenAI(api_key=api_key)

    # ── public API ───────────────────────────────────────────────────────

    @retry(max_attempts=3, base_delay=2.0, exceptions=(openai.APIError,))
    def generate(
        self,
        script: dict[str, Any],
        channel_profile: ChannelProfile,
        platforms: list[str] | None = None,
    ) -> dict[str, Any]:
        """Repurpose a video script into social media content.

        Args:
            script: A script dict (as returned by the script generators)
                containing at minimum *title*, *description*, *sections*,
                *hook*, *outro*, and *tags*.
            platforms: Platform keys to generate for.  Defaults to
                :data:`ALL_PLATFORMS`.
            channel_profile: The channel profile (niche, tone, audience).

        Returns:
            A dict keyed by platform name, each value being the
            platform-specific content dict.

        Raises:
            ValueError: If any requested platform is unknown, or the API
                returns invalid JSON.
            openai.APIError: On transient OpenAI failures (retried
                automatically up to 3 times).
        """
        platforms = platforms or list(ALL_PLATFORMS)

        # Validate requested platforms
        unknown = set(platforms) - set(ALL_PLATFORMS)
        if unknown:
            raise ValueError(
                f"Unknown platform(s): {unknown!r}. "
                f"Supported: {ALL_PLATFORMS}"
            )

        self.logger.info(
            "Repurposing script %r for platforms: %s",
            script.get("title", "untitled"),
            ", ".join(platforms),
        )

        # Build a trimmed schema containing only the requested platforms
        trimmed_schema = self._build_trimmed_schema(platforms)

        system = _SYSTEM_PROMPT.format(
            schema=json.dumps(trimmed_schema, indent=2),
        )

        sections_text = _format_sections(script.get("sections", []))

        user_msg = _USER_TEMPLATE.format(
            platforms=", ".join(platforms),
            title=script.get("title", ""),
            description=script.get("description", ""),
            hook=script.get("hook", ""),
            outro=script.get("outro", ""),
            tags=", ".join(script.get("tags", [])),
            niche=channel_profile.niche,
            tone=channel_profile.content.tone,
            target_audience=channel_profile.target_audience,
            sections_text=sections_text,
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
            result: dict[str, Any] = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            self.logger.error("OpenAI returned invalid JSON: %s", exc)
            raise ValueError("OpenAI response was not valid JSON") from exc

        # Ensure we only return the platforms that were requested
        result = {k: v for k, v in result.items() if k in platforms}

        missing = set(platforms) - set(result.keys())
        if missing:
            self.logger.warning(
                "OpenAI response missing platforms: %s — they will be absent "
                "from the result.",
                ", ".join(sorted(missing)),
            )

        self.logger.info(
            "Repurposing complete: generated content for %d/%d platforms",
            len(result),
            len(platforms),
        )
        return result

    # ── internals ────────────────────────────────────────────────────────

    @staticmethod
    def _build_trimmed_schema(platforms: list[str]) -> dict[str, Any]:
        """Return a copy of REPURPOSE_SCHEMA with only *platforms* present."""
        trimmed: dict[str, Any] = {
            "type": "object",
            "required": list(platforms),
            "properties": {},
        }
        for platform in platforms:
            if platform in REPURPOSE_SCHEMA["properties"]:
                trimmed["properties"][platform] = REPURPOSE_SCHEMA[
                    "properties"
                ][platform]
        return trimmed
