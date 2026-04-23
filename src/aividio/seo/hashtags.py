"""Platform-specific hashtag generation strategies."""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic

from aividio.config.settings import Settings, get_settings
from aividio.utils.retry import retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Platform strategy configs
# ---------------------------------------------------------------------------

_PLATFORM_CONFIGS: dict[str, dict[str, Any]] = {
    "youtube": {
        "count_min": 3,
        "count_max": 5,
        "strategy": "high-relevance only — YouTube penalises spammy hashtags",
        "rules": [
            "3-5 hashtags maximum",
            "Place in description, not title",
            "Use #Shorts if it is a short-form video",
            "First 3 hashtags appear above the title on YouTube",
            "Focus on exact-topic and niche hashtags",
        ],
    },
    "tiktok": {
        "count_min": 3,
        "count_max": 8,
        "strategy": "mix trending + niche + branded for FYP reach",
        "rules": [
            "3-8 hashtags",
            "Include 1-2 trending/viral hashtags (e.g., #fyp, #foryou)",
            "Include 2-3 niche-specific hashtags",
            "Include 1 branded hashtag if applicable",
            "Keep them short — TikTok truncates long captions",
        ],
    },
    "instagram": {
        "count_min": 20,
        "count_max": 30,
        "strategy": "tiered groups — high-reach, medium, and niche",
        "rules": [
            "20-30 hashtags for maximum reach",
            "Tier 1 (5-8): high-reach, broad hashtags (100K+ posts)",
            "Tier 2 (8-12): medium-reach, category hashtags (10K-100K posts)",
            "Tier 3 (5-10): niche / low-competition hashtags (<10K posts)",
            "Include 1-2 branded or campaign hashtags",
            "Place in first comment or end of caption",
        ],
    },
}

_HASHTAG_SYSTEM = """\
You are a social media hashtag strategist.  Generate hashtags optimised for \
the specified platform using the strategy below.

Platform: {platform}
Strategy: {strategy}

Rules:
{rules}

Return **strict JSON** — a single array of hashtag strings (include the # \
prefix).  No markdown fences, no commentary.
"""

_HASHTAG_USER = """\
Generate {platform} hashtags for this video content:

Title: {title}
Description: {description}
Topic keywords: {keywords}
Niche: {niche}

Target count: {count_min}-{count_max} hashtags.
"""


class HashtagGenerator:
    """Generate platform-specific hashtags for video content."""

    MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 1024

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        api_key = self.settings.anthropic_api_key.get_secret_value()
        if not api_key:
            raise ValueError(
                "anthropic_api_key is not configured.  "
                "Set AIVIDIO_ANTHROPIC_API_KEY in your environment."
            )
        self._client = anthropic.Anthropic(api_key=api_key)

    @retry(max_attempts=3, base_delay=2.0, exceptions=(anthropic.APIError,))
    def _ask_claude(self, system: str, user: str) -> str:
        response = self._client.messages.create(
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text.strip()

    def _parse_json(self, raw: str) -> list[str]:
        text = raw
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()
        try:
            result = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON from hashtag generation: %s", exc)
            raise ValueError("Claude response was not valid JSON") from exc
        if not isinstance(result, list):
            raise ValueError(f"Expected a JSON array, got {type(result).__name__}")
        return [str(h) for h in result]

    def generate(
        self,
        script: dict,
        platform: str = "youtube",
        niche: str = "general",
    ) -> list[str]:
        """Generate hashtags tailored for the given platform.

        Args:
            script: Video script dict (must have at least ``title``).
            platform: One of ``youtube``, ``tiktok``, ``instagram``.
            niche: Content niche for more targeted hashtags.

        Returns:
            List of hashtag strings, each prefixed with ``#``.
        """
        platform = platform.lower()
        config = _PLATFORM_CONFIGS.get(platform)
        if config is None:
            supported = ", ".join(sorted(_PLATFORM_CONFIGS))
            raise ValueError(
                f"Unsupported platform '{platform}'.  Supported: {supported}"
            )

        title = script.get("title", "")
        description = script.get("description", "")
        keywords = ", ".join(script.get("tags", [])[:10]) if script.get("tags") else title

        logger.info("Generating %s hashtags for %r", platform, title)

        system = _HASHTAG_SYSTEM.format(
            platform=platform.title(),
            strategy=config["strategy"],
            rules="\n".join(f"- {r}" for r in config["rules"]),
        )

        user = _HASHTAG_USER.format(
            platform=platform.title(),
            title=title,
            description=description[:300],
            keywords=keywords,
            niche=niche,
            count_min=config["count_min"],
            count_max=config["count_max"],
        )

        raw = self._ask_claude(system=system, user=user)
        hashtags = self._parse_json(raw)

        # Ensure # prefix
        hashtags = [h if h.startswith("#") else f"#{h}" for h in hashtags]

        # Enforce platform limits
        max_count = config["count_max"]
        if len(hashtags) > max_count:
            hashtags = hashtags[:max_count]

        logger.info("Generated %d %s hashtags", len(hashtags), platform)
        return hashtags

    def generate_youtube(self, script: dict, niche: str = "general") -> list[str]:
        """Convenience: generate YouTube hashtags (3-5, high relevance)."""
        return self.generate(script=script, platform="youtube", niche=niche)

    def generate_tiktok(self, script: dict, niche: str = "general") -> list[str]:
        """Convenience: generate TikTok hashtags (trending + niche mix)."""
        return self.generate(script=script, platform="tiktok", niche=niche)

    def generate_instagram(self, script: dict, niche: str = "general") -> list[str]:
        """Convenience: generate Instagram hashtags (20-30, tiered reach)."""
        return self.generate(script=script, platform="instagram", niche=niche)
