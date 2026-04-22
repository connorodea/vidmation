"""SEO optimizer — improve video metadata for YouTube search and discovery."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import anthropic

from aividio.config.settings import Settings, get_settings
from aividio.seo.hashtags import HashtagGenerator
from aividio.utils.retry import retry

if TYPE_CHECKING:
    from aividio.config.profiles import ChannelProfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_TITLE_SYSTEM = """\
You are a YouTube SEO specialist.  You optimise video titles for maximum \
click-through rate (CTR) while maintaining accuracy.

Rules:
- Each title must be UNDER 60 characters (mobile-friendly).
- Front-load the most important keyword.
- Include at least one power word OR a number where natural.
- Create a curiosity gap without being misleading.
- Avoid ALL-CAPS gimmicks.  Title-case is fine.

Return **strict JSON** — no markdown fences, no commentary outside the JSON \
array.
"""

_TITLE_USER = """\
Generate {count} title variations for a YouTube video.

Original title: {title}
Topic: {topic}
Niche: {niche}

Return a JSON array of objects:
[
  {{
    "title": "...",
    "estimated_ctr_score": 0.0-1.0,
    "power_words_used": ["..."],
    "character_count": <int>
  }}
]
Sort by estimated_ctr_score descending.
"""

_DESC_SYSTEM = """\
You are a YouTube SEO copywriter.  You write descriptions that hook viewers, \
improve search ranking, and encourage engagement.

Return **strict JSON** with a single key "description" whose value is the \
fully-formatted description text (use \\n for newlines).
"""

_DESC_USER = """\
Write a YouTube description for the following video.

Script title: {title}
Script hook: {hook}
Sections: {sections_summary}
Channel name: {channel_name}
Channel niche: {niche}
Subscribe CTA style: {cta_style}
Affiliate / sponsor note: {affiliate_note}

Requirements:
1. First 2 lines: a compelling hook + keyword-rich summary (visible before \
   "Show More").
2. Timestamps for each section (use 0:00, 1:30, etc.).
3. 3-5 relevant hashtags at the end.
4. A subscribe + bell CTA.
5. If affiliate/sponsor info is provided, include a clearly marked section.
"""

_TAGS_SYSTEM = """\
You are a YouTube tag researcher.  Generate a JSON array of tag strings \
optimised for search.  Mix exact-match, broad-match, long-tail, and related \
topic tags.  Total characters of ALL tags combined must be under 500 \
(YouTube's hard limit).  Return only the JSON array — no fences, no keys.
"""

_TAGS_USER = """\
Generate YouTube tags for this video.

Title: {title}
Description: {description}
Topic: {topic}
Niche: {niche}
Max tags: {max_tags}
"""

_KEYWORD_SYSTEM = """\
You are a YouTube keyword research analyst.  Analyse keyword opportunity \
and return a JSON object with the fields: primary_keywords (list), \
secondary_keywords (list), long_tail (list), competition_estimate \
("low"/"medium"/"high"), suggested_angles (list of strings).
No markdown fences.
"""

_KEYWORD_USER = """\
Analyse keyword opportunity for YouTube videos about:

Topic: {topic}
Niche: {niche}

Consider search volume potential, competition, and content gap opportunity.
"""

_COMPETITION_SYSTEM = """\
You are a competitive content analyst for YouTube.  Analyse what would \
already be ranking for the given topic and return a JSON object with: \
content_gaps (list), unique_angles (list), recommended_approach (string).
No markdown fences.
"""

_COMPETITION_USER = """\
Analyse what's already ranking on YouTube for:

Topic: {topic}

Identify content gaps and unique angles a new video could take.
"""


class SEOOptimizer:
    """Optimise video metadata for YouTube search and discovery."""

    MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 4096

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        api_key = self.settings.anthropic_api_key.get_secret_value()
        if not api_key:
            raise ValueError(
                "anthropic_api_key is not configured.  "
                "Set VIDMATION_ANTHROPIC_API_KEY in your environment."
            )
        self._client = anthropic.Anthropic(api_key=api_key)
        self._hashtag_gen = HashtagGenerator(settings=self.settings)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @retry(max_attempts=3, base_delay=2.0, exceptions=(anthropic.APIError,))
    def _ask_claude(self, system: str, user: str) -> str:
        """Send a prompt to Claude and return the raw text response."""
        response = self._client.messages.create(
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text.strip()

    def _parse_json(self, raw: str) -> Any:
        """Strip optional markdown fences and parse JSON."""
        text = raw
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error("Claude returned invalid JSON: %s — raw: %s", exc, text[:300])
            raise ValueError("Claude response was not valid JSON") from exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def optimize_title(
        self,
        title: str,
        topic: str,
        niche: str,
        count: int = 8,
    ) -> list[dict]:
        """Generate 5-10 title variations optimised for CTR.

        Returns a list of dicts, each containing:
            - title (str)
            - estimated_ctr_score (float 0-1)
            - power_words_used (list[str])
            - character_count (int)
        """
        count = max(5, min(count, 10))
        logger.info("Generating %d title variations for topic=%r", count, topic)

        raw = self._ask_claude(
            system=_TITLE_SYSTEM,
            user=_TITLE_USER.format(
                count=count,
                title=title,
                topic=topic,
                niche=niche,
            ),
        )
        titles: list[dict] = self._parse_json(raw)

        # Validate and enforce character limit
        valid: list[dict] = []
        for t in titles:
            t["character_count"] = len(t.get("title", ""))
            if t["character_count"] <= 60:
                valid.append(t)
            else:
                # Truncate gracefully — keep but flag it
                logger.warning("Title over 60 chars (%d): %s", t["character_count"], t["title"])
                valid.append(t)

        valid.sort(key=lambda x: x.get("estimated_ctr_score", 0), reverse=True)
        return valid

    def optimize_description(
        self,
        script: dict,
        channel: ChannelProfile,
        affiliate_note: str = "",
    ) -> str:
        """Generate a YouTube description with hook, timestamps, hashtags, and CTA.

        Args:
            script: The video script dict (matching SCRIPT_SCHEMA).
            channel: The channel profile for branding / CTA configuration.
            affiliate_note: Optional affiliate or sponsor disclosure text.

        Returns:
            The fully-formatted description string.
        """
        sections_summary = "; ".join(
            f"Section {s.get('section_number', i + 1)}: {s.get('heading', 'Untitled')}"
            for i, s in enumerate(script.get("sections", []))
        )

        logger.info("Generating SEO description for %r", script.get("title", "untitled"))

        raw = self._ask_claude(
            system=_DESC_SYSTEM,
            user=_DESC_USER.format(
                title=script.get("title", ""),
                hook=script.get("hook", ""),
                sections_summary=sections_summary,
                channel_name=channel.name,
                niche=channel.niche,
                cta_style=channel.content.cta_style,
                affiliate_note=affiliate_note or "None",
            ),
        )

        parsed = self._parse_json(raw)
        if isinstance(parsed, dict):
            return parsed.get("description", str(parsed))
        return str(parsed)

    def generate_tags(
        self,
        script: dict,
        max_tags: int = 30,
    ) -> list[str]:
        """Generate YouTube tags optimised for search.

        Mixes exact-match, broad-match, long-tail, and related-topic tags.
        Total characters stay under 500 (YouTube's limit).
        """
        max_tags = min(max_tags, 30)

        logger.info("Generating up to %d tags for %r", max_tags, script.get("title", ""))

        raw = self._ask_claude(
            system=_TAGS_SYSTEM,
            user=_TAGS_USER.format(
                title=script.get("title", ""),
                description=script.get("description", ""),
                topic=script.get("title", ""),
                niche="general",
                max_tags=max_tags,
            ),
        )

        tags: list[str] = self._parse_json(raw)

        # Enforce YouTube's 500-character cumulative limit
        kept: list[str] = []
        total_chars = 0
        for tag in tags:
            tag = tag.strip()
            if not tag:
                continue
            if total_chars + len(tag) > 500:
                break
            kept.append(tag)
            total_chars += len(tag)

        logger.info("Returning %d tags (%d total chars)", len(kept), total_chars)
        return kept

    def generate_hashtags(
        self,
        script: dict,
        platform: str = "youtube",
    ) -> list[str]:
        """Platform-specific hashtag generation.

        Delegates to :class:`HashtagGenerator` for platform-aware strategies.
        """
        return self._hashtag_gen.generate(script=script, platform=platform)

    def keyword_research(self, topic: str, niche: str) -> dict:
        """Analyse keyword opportunity using Claude.

        Returns:
            Dict with keys: primary_keywords, secondary_keywords, long_tail,
            competition_estimate, suggested_angles.
        """
        logger.info("Running keyword research for topic=%r niche=%r", topic, niche)

        raw = self._ask_claude(
            system=_KEYWORD_SYSTEM,
            user=_KEYWORD_USER.format(topic=topic, niche=niche),
        )
        return self._parse_json(raw)

    def analyze_competition(self, topic: str) -> dict:
        """Analyse what is already ranking for this topic.

        Returns:
            Dict with keys: content_gaps, unique_angles, recommended_approach.
        """
        logger.info("Analysing competition for topic=%r", topic)

        raw = self._ask_claude(
            system=_COMPETITION_SYSTEM,
            user=_COMPETITION_USER.format(topic=topic),
        )
        return self._parse_json(raw)
