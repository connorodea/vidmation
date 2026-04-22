"""YouTube metadata generator — AI-optimized titles, descriptions, and tags."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import openai

from aividio.config.profiles import ChannelProfile
from aividio.services.base import BaseService
from aividio.utils.retry import retry

if TYPE_CHECKING:
    from aividio.config.settings import Settings

# YouTube API limits.
_MAX_TITLE_LENGTH = 100
_MAX_DESCRIPTION_LENGTH = 5000
_MAX_TAGS_TOTAL_CHARS = 500
_MIN_TAGS = 15
_MAX_TAGS = 30
_MIN_HASHTAGS = 3
_MAX_HASHTAGS = 5

_METADATA_SCHEMA = {
    "type": "object",
    "required": [
        "title",
        "description_hook",
        "hashtags",
        "tags",
        "category_id",
        "cta_text",
    ],
    "properties": {
        "title": {
            "type": "string",
            "description": (
                "SEO-optimized, attention-grabbing YouTube title. "
                "Must be under 100 characters. Click-worthy but NOT clickbait."
            ),
        },
        "description_hook": {
            "type": "string",
            "description": (
                "Compelling 2-3 sentence opening paragraph for the description. "
                "Should entice viewers to watch the full video."
            ),
        },
        "hashtags": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": _MIN_HASHTAGS,
            "maxItems": _MAX_HASHTAGS,
            "description": "3-5 relevant hashtags (without the # symbol).",
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": _MIN_TAGS,
            "maxItems": _MAX_TAGS,
            "description": (
                "15-30 relevant YouTube SEO tags. Mix of broad and "
                "specific/long-tail keywords."
            ),
        },
        "category_id": {
            "type": "string",
            "description": (
                "YouTube video category ID as a string. Common: "
                '"22" (People & Blogs), "27" (Education), '
                '"28" (Science & Technology), "24" (Entertainment).'
            ),
        },
        "cta_text": {
            "type": "string",
            "description": (
                "A short call-to-action sentence encouraging likes, "
                "subscribes, and comments."
            ),
        },
    },
}

_SYSTEM_PROMPT = """\
You are a YouTube SEO and metadata expert. Your job is to generate \
optimized metadata that maximises click-through rate, watch time, and \
discoverability while remaining honest and accurate.

Return **only** valid JSON matching the schema below — no markdown \
fences, no extra text.

JSON Schema:
{schema}

Rules:
- Title: Under 100 characters. Use power words, numbers, or curiosity \
  gaps where appropriate. Must accurately reflect the content.
- Description hook: 2-3 engaging sentences that complement the title \
  and make viewers want to watch.
- Hashtags: 3-5 highly relevant hashtags (no # symbol). Mix trending \
  and niche-specific.
- Tags: 15-30 tags. Include exact-match keywords, synonyms, related \
  topics, and long-tail variations. Total combined character count of \
  all tags must be under 500 characters.
- Category ID: Choose the most appropriate YouTube category.
- CTA: Natural, non-pushy call to action matching the channel tone.
"""

_USER_TEMPLATE = """\
Generate optimized YouTube metadata for the following video:

**Video Title (from script):** {script_title}
**Video Description (from script):** {script_description}
**Video Hook:** {script_hook}
**Number of Sections:** {num_sections}
**Estimated Duration:** {duration} seconds (~{duration_min} minutes)
**Script Tags:** {script_tags}

**Channel Profile:**
- Channel: {channel_name}
- Niche: {niche}
- Target Audience: {target_audience}
- Tone: {tone}
- CTA Style: {cta_style}
- Default Category: {default_category}
"""


def _format_timestamp(total_seconds: int) -> str:
    """Convert seconds to YouTube timestamp format (M:SS or H:MM:SS)."""
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def generate_description_with_chapters(
    script: dict,
    description_hook: str,
    hashtags: list[str],
    cta_text: str,
    links_section: str = "",
) -> str:
    """Build a full YouTube description with auto-generated chapters.

    Takes the script sections and their estimated durations to produce
    properly formatted YouTube timestamp chapters.

    Args:
        script: The video script dict with ``sections``, each having
            ``title`` and ``estimated_duration_seconds``.
        description_hook: The AI-generated opening paragraph.
        hashtags: List of hashtags (without ``#`` prefix).
        cta_text: Call-to-action text.
        links_section: Optional links/credits block to append.

    Returns:
        The fully formatted YouTube description string, truncated to
        5000 characters.
    """
    parts: list[str] = []

    # --- Hook paragraph ---
    parts.append(description_hook.strip())
    parts.append("")

    # --- Chapters / Timestamps ---
    sections = script.get("sections", [])
    if sections:
        parts.append("CHAPTERS")
        elapsed = 0
        for section in sections:
            title = section.get("title", "Untitled")
            timestamp = _format_timestamp(elapsed)
            parts.append(f"{timestamp} - {title}")
            elapsed += section.get("estimated_duration_seconds", 0)
        parts.append("")

    # --- CTA ---
    parts.append(cta_text.strip())
    parts.append("")

    # --- Hashtags ---
    if hashtags:
        hashtag_line = " ".join(f"#{tag}" for tag in hashtags)
        parts.append(hashtag_line)
        parts.append("")

    # --- Links / Credits ---
    if links_section:
        parts.append(links_section.strip())
        parts.append("")

    description = "\n".join(parts).strip()
    return description[:_MAX_DESCRIPTION_LENGTH]


class YouTubeMetadataGenerator(BaseService):
    """Generate optimized YouTube metadata using OpenAI GPT-4o.

    Produces SEO-friendly titles, descriptions with chapters, tags,
    and hashtags from a video script and channel profile.
    """

    MODEL = "gpt-4o"
    MAX_TOKENS = 2048

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
    def generate(
        self,
        script: dict,
        channel_profile: ChannelProfile,
        *,
        title_override: str | None = None,
        description_override: str | None = None,
        tags_override: list[str] | None = None,
        category_id_override: str | None = None,
        hashtags_override: list[str] | None = None,
        links_section: str = "",
    ) -> dict[str, Any]:
        """Generate optimized YouTube metadata from a video script.

        Args:
            script: Video script dict with keys: ``title``,
                ``description``, ``sections``, ``tags``, ``hook``,
                ``outro``, ``total_estimated_duration_seconds``.
            channel_profile: The channel's configuration profile.
            title_override: If provided, skip AI title generation.
            description_override: If provided, use as full description.
            tags_override: If provided, use instead of AI-generated tags.
            category_id_override: Override the category selection.
            hashtags_override: Override the hashtag selection.
            links_section: Optional links/credits block for description.

        Returns:
            A dict with keys: ``title``, ``description``, ``tags``,
            ``category_id``, ``default_language``, ``hashtags``.
        """
        self.logger.info(
            "Generating YouTube metadata for script: %r",
            script.get("title", "untitled"),
        )

        # --- Call AI for metadata ---
        ai_metadata = self._call_openai(script, channel_profile)

        # --- Apply overrides ---
        title = title_override or ai_metadata.get("title", script.get("title", ""))
        title = title[:_MAX_TITLE_LENGTH]

        hashtags = hashtags_override or ai_metadata.get("hashtags", [])
        hashtags = hashtags[:_MAX_HASHTAGS]

        cta_text = ai_metadata.get("cta_text", "")
        description_hook = ai_metadata.get(
            "description_hook", script.get("description", "")
        )

        if description_override:
            description = description_override[:_MAX_DESCRIPTION_LENGTH]
        else:
            description = generate_description_with_chapters(
                script=script,
                description_hook=description_hook,
                hashtags=hashtags,
                cta_text=cta_text,
                links_section=links_section,
            )

        tags = tags_override or ai_metadata.get("tags", script.get("tags", []))
        tags = self._enforce_tag_limits(tags)

        category_id = (
            category_id_override
            or ai_metadata.get("category_id")
            or channel_profile.youtube.category_id
        )

        default_language = channel_profile.youtube.default_language

        metadata = {
            "title": title,
            "description": description,
            "tags": tags,
            "category_id": str(category_id),
            "default_language": default_language,
            "hashtags": hashtags,
        }

        self.logger.info(
            "Metadata generated: title=%r (%d chars), tags=%d, description=%d chars",
            metadata["title"],
            len(metadata["title"]),
            len(metadata["tags"]),
            len(metadata["description"]),
        )

        return metadata

    def _call_openai(
        self, script: dict, channel_profile: ChannelProfile
    ) -> dict[str, Any]:
        """Call GPT-4o to generate optimized metadata fields."""
        sections = script.get("sections", [])
        total_duration = script.get(
            "total_estimated_duration_seconds",
            sum(s.get("estimated_duration_seconds", 0) for s in sections),
        )

        system = _SYSTEM_PROMPT.format(
            schema=json.dumps(_METADATA_SCHEMA, indent=2)
        )

        user_msg = _USER_TEMPLATE.format(
            script_title=script.get("title", "Untitled"),
            script_description=script.get("description", ""),
            script_hook=script.get("hook", ""),
            num_sections=len(sections),
            duration=total_duration,
            duration_min=round(total_duration / 60, 1),
            script_tags=", ".join(script.get("tags", [])) or "none",
            channel_name=channel_profile.name,
            niche=channel_profile.niche,
            target_audience=channel_profile.target_audience,
            tone=channel_profile.content.tone,
            cta_style=channel_profile.content.cta_style,
            default_category=channel_profile.youtube.category_id,
        )

        self.logger.debug("Calling OpenAI GPT-4o for metadata generation")

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
            raise ValueError("OpenAI metadata response was not valid JSON") from exc

        return result

    @staticmethod
    def _enforce_tag_limits(tags: list[str]) -> list[str]:
        """Trim the tag list so total characters stay under 500.

        YouTube counts tags as comma-separated, so each tag's length
        plus separators must fit within the limit.
        """
        kept: list[str] = []
        total_chars = 0

        for tag in tags:
            tag = tag.strip()
            if not tag:
                continue
            # YouTube counts the tag itself; commas are implicit separators.
            addition = len(tag) + (2 if kept else 0)  # ", " between tags
            if total_chars + addition > _MAX_TAGS_TOTAL_CHARS:
                break
            kept.append(tag)
            total_chars += addition

        return kept
