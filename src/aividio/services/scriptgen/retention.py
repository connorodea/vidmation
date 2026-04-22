"""Retention optimization engine — analyzes and enhances scripts for viewer retention."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import anthropic

from aividio.config.profiles import ChannelProfile
from aividio.services.base import BaseService
from aividio.utils.retry import retry

if TYPE_CHECKING:
    from aividio.config.settings import Settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class SectionScore:
    """Retention score and feedback for a single script section."""

    section_number: int
    heading: str
    retention_score: float  # 0.0 – 1.0
    risk_level: str  # "low", "medium", "high"
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class RetentionAnalysis:
    """Full retention analysis of a video script."""

    overall_score: float  # 0.0 – 1.0
    hook_score: float
    pacing_score: float
    curiosity_score: float
    emotional_variety_score: float
    cta_placement_score: float
    section_scores: list[SectionScore] = field(default_factory=list)
    summary: str = ""
    top_risks: list[str] = field(default_factory=list)
    top_recommendations: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_ANALYSIS_SYSTEM = """\
You are an expert YouTube audience-retention analyst.  Given a faceless-channel \
video script in JSON, you produce a retention analysis in **strict JSON** — no \
markdown fences, no commentary outside the JSON object.

Evaluate:
1. Hook strength (first 5 seconds of narration).
2. Pattern interrupt frequency — should be every 30-45 seconds.
3. Open loops and curiosity gaps that keep viewers watching.
4. Emotional pacing — variety of emotions (surprise, humor, tension, relief).
5. CTA placement timing — not too early, not buried at the end.

Return JSON matching this structure exactly:
{
  "overall_score": <0.0-1.0>,
  "hook_score": <0.0-1.0>,
  "pacing_score": <0.0-1.0>,
  "curiosity_score": <0.0-1.0>,
  "emotional_variety_score": <0.0-1.0>,
  "cta_placement_score": <0.0-1.0>,
  "section_scores": [
    {
      "section_number": <int>,
      "heading": "<string>",
      "retention_score": <0.0-1.0>,
      "risk_level": "low|medium|high",
      "issues": ["..."],
      "suggestions": ["..."]
    }
  ],
  "summary": "<1-2 sentence overview>",
  "top_risks": ["<top 3 retention risks>"],
  "top_recommendations": ["<top 3 actionable fixes>"]
}
"""

_OPTIMIZE_SYSTEM = """\
You are a YouTube script optimizer specializing in viewer retention.  You will \
receive a video script and its retention analysis.  Rewrite the script to fix \
all identified issues while preserving the original topic and information.

Rules:
- Strengthen the hook if score < 0.7.
- Add a pattern interrupt (question, "but here's the thing...", surprising fact) \
  every 30-45 seconds of estimated narration.
- Insert curiosity gaps before each section transition: hint at what comes next \
  without revealing it.
- Vary emotional tone across sections — do not stay monotone.
- Place a soft CTA mid-video and a strong CTA in the outro.
- Keep narration conversational, paced for voiceover (~150 words/minute).

Return the complete rewritten script as **strict JSON** matching the original \
schema — no markdown fences, no commentary.
"""

_HOOKS_SYSTEM = """\
You are a YouTube hook specialist.  Generate hook variations for A/B testing.  \
Each hook must grab attention in the first 5 seconds.

Styles to use: question, bold_claim, statistic, story_tease, controversy, \
relatable_pain, curiosity_gap.

Return **strict JSON** — an array of objects:
[
  {
    "text": "<the hook text>",
    "style": "<style name>",
    "estimated_retention_score": <0.0-1.0>
  }
]
"""

_TITLES_SYSTEM = """\
You are a YouTube title and CTR optimization expert.  Given a video script, \
generate title variations optimized for click-through rate.

Use proven patterns: numbers, curiosity gaps, power words, brackets [SHOCKING], \
how-to, listicle, vs., "I tried X for Y days", "Nobody talks about X".

Return **strict JSON** — an array of objects:
[
  {
    "title": "<the title>",
    "style": "<pattern used>",
    "ctr_prediction": <0.0-1.0>
  }
]
"""

_THUMBNAIL_SYSTEM = """\
You are a YouTube thumbnail concept designer.  Given a video script, generate \
thumbnail concepts that drive clicks.

Each concept should specify:
- A strong visual concept (emotion, contrast, curiosity).
- An image generation prompt suitable for AI image generators (DALL-E / Flux).
- Primary text overlay (max 4 words, large and bold).
- Optional secondary text (smaller, supporting).
- Visual style (cinematic, cartoon, minimalist, split-screen, before-after).

Return **strict JSON** — an array of objects:
[
  {
    "concept": "<description of the thumbnail idea>",
    "image_prompt": "<detailed AI image generation prompt>",
    "primary_text": "<max 4 words>",
    "secondary_text": "<optional supporting text or empty string>",
    "style": "<visual style>"
  }
]
"""


class RetentionOptimizer(BaseService):
    """Analyzes and enhances scripts for maximum viewer retention.

    Uses Claude to evaluate hook strength, pacing, curiosity gaps,
    emotional variety, and CTA placement — then rewrites weak sections.
    """

    MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 8192

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__(settings=settings)
        api_key = self.settings.anthropic_api_key.get_secret_value()
        if not api_key:
            raise ValueError(
                "anthropic_api_key is not configured. "
                "Set VIDMATION_ANTHROPIC_API_KEY in your environment."
            )
        self._client = anthropic.Anthropic(api_key=api_key)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_claude(self, system: str, user_message: str, max_tokens: int | None = None) -> str:
        """Send a request to Claude and return the raw text response."""
        response = self._client.messages.create(
            model=self.MODEL,
            max_tokens=max_tokens or self.MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text.strip()

        # Strip markdown code fences if the model wraps them.
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]

        return raw.strip()

    def _parse_json(self, raw: str, context: str = "Claude") -> Any:
        """Parse a JSON string, raising a clear error on failure."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            self.logger.error("%s returned invalid JSON: %s\nRaw: %s", context, exc, raw[:500])
            raise ValueError(f"{context} response was not valid JSON") from exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @retry(max_attempts=3, base_delay=2.0, exceptions=(anthropic.APIError,))
    def analyze(self, script: dict) -> RetentionAnalysis:
        """Score script sections for retention risk.

        Evaluates hook strength, pattern interrupt frequency, open loops,
        emotional pacing, and CTA placement timing.

        Args:
            script: A video script dict matching SCRIPT_SCHEMA.

        Returns:
            A :class:`RetentionAnalysis` with per-section scores and recommendations.
        """
        self.logger.info("Analyzing retention for script: %r", script.get("title", "untitled"))

        raw = self._call_claude(
            system=_ANALYSIS_SYSTEM,
            user_message=f"Analyze this script for retention:\n\n{json.dumps(script, indent=2)}",
        )

        data = self._parse_json(raw, context="RetentionAnalysis")

        section_scores = [
            SectionScore(
                section_number=s.get("section_number", 0),
                heading=s.get("heading", ""),
                retention_score=float(s.get("retention_score", 0.0)),
                risk_level=s.get("risk_level", "medium"),
                issues=s.get("issues", []),
                suggestions=s.get("suggestions", []),
            )
            for s in data.get("section_scores", [])
        ]

        analysis = RetentionAnalysis(
            overall_score=float(data.get("overall_score", 0.0)),
            hook_score=float(data.get("hook_score", 0.0)),
            pacing_score=float(data.get("pacing_score", 0.0)),
            curiosity_score=float(data.get("curiosity_score", 0.0)),
            emotional_variety_score=float(data.get("emotional_variety_score", 0.0)),
            cta_placement_score=float(data.get("cta_placement_score", 0.0)),
            section_scores=section_scores,
            summary=data.get("summary", ""),
            top_risks=data.get("top_risks", []),
            top_recommendations=data.get("top_recommendations", []),
        )

        self.logger.info(
            "Retention analysis complete: overall=%.2f, hook=%.2f, pacing=%.2f",
            analysis.overall_score,
            analysis.hook_score,
            analysis.pacing_score,
        )
        return analysis

    @retry(max_attempts=3, base_delay=2.0, exceptions=(anthropic.APIError,))
    def optimize(self, script: dict, profile: ChannelProfile) -> dict:
        """Rewrite weak sections for better retention.

        Adds pattern interrupts, strengthens hooks, inserts curiosity gaps,
        and improves emotional pacing.

        Args:
            script: The original script dict.
            profile: Channel profile for tone and style context.

        Returns:
            An optimized script dict with the same schema.
        """
        self.logger.info("Optimizing script for retention: %r", script.get("title", "untitled"))

        # First, get the analysis so we can include it in the optimization prompt.
        analysis = self.analyze(script)

        analysis_summary = {
            "overall_score": analysis.overall_score,
            "hook_score": analysis.hook_score,
            "pacing_score": analysis.pacing_score,
            "curiosity_score": analysis.curiosity_score,
            "emotional_variety_score": analysis.emotional_variety_score,
            "cta_placement_score": analysis.cta_placement_score,
            "top_risks": analysis.top_risks,
            "top_recommendations": analysis.top_recommendations,
            "section_scores": [
                {
                    "section_number": s.section_number,
                    "heading": s.heading,
                    "retention_score": s.retention_score,
                    "risk_level": s.risk_level,
                    "issues": s.issues,
                    "suggestions": s.suggestions,
                }
                for s in analysis.section_scores
            ],
        }

        user_message = (
            f"Channel profile:\n"
            f"- Niche: {profile.niche}\n"
            f"- Tone: {profile.content.tone}\n"
            f"- Target audience: {profile.target_audience}\n\n"
            f"Retention analysis:\n{json.dumps(analysis_summary, indent=2)}\n\n"
            f"Original script:\n{json.dumps(script, indent=2)}\n\n"
            f"Rewrite this script to fix all retention issues identified above."
        )

        raw = self._call_claude(system=_OPTIMIZE_SYSTEM, user_message=user_message)
        optimized = self._parse_json(raw, context="Optimization")

        self.logger.info(
            "Script optimized: %r (%d sections)",
            optimized.get("title", "untitled"),
            len(optimized.get("sections", [])),
        )
        return optimized

    @retry(max_attempts=3, base_delay=2.0, exceptions=(anthropic.APIError,))
    def generate_hooks(self, topic: str, count: int = 5) -> list[dict]:
        """Generate multiple hook variations for A/B testing.

        Args:
            topic: The video topic.
            count: Number of hook variations to generate.

        Returns:
            List of ``{"text": str, "style": str, "estimated_retention_score": float}``
        """
        self.logger.info("Generating %d hook variations for topic=%r", count, topic)

        raw = self._call_claude(
            system=_HOOKS_SYSTEM,
            user_message=(
                f"Generate exactly {count} hook variations for this video topic:\n\n"
                f"{topic}\n\n"
                f"Each hook should use a different style and grab attention in 5 seconds."
            ),
            max_tokens=4096,
        )

        hooks = self._parse_json(raw, context="HookGeneration")

        if not isinstance(hooks, list):
            raise ValueError("Expected a JSON array of hook objects")

        self.logger.info("Generated %d hooks for topic=%r", len(hooks), topic)
        return hooks

    @retry(max_attempts=3, base_delay=2.0, exceptions=(anthropic.APIError,))
    def generate_titles(self, script: dict, count: int = 10) -> list[dict]:
        """Generate title variations optimized for click-through rate.

        Args:
            script: The video script dict.
            count: Number of title variations to generate.

        Returns:
            List of ``{"title": str, "style": str, "ctr_prediction": float}``
        """
        self.logger.info("Generating %d title variations", count)

        raw = self._call_claude(
            system=_TITLES_SYSTEM,
            user_message=(
                f"Generate exactly {count} YouTube title variations for this script:\n\n"
                f"Current title: {script.get('title', 'N/A')}\n"
                f"Topic: {script.get('description', 'N/A')}\n"
                f"Tags: {', '.join(script.get('tags', []))}\n\n"
                f"Script hook: {script.get('hook', 'N/A')}\n\n"
                f"Section headings: {', '.join(s.get('heading', '') for s in script.get('sections', []))}"
            ),
            max_tokens=4096,
        )

        titles = self._parse_json(raw, context="TitleGeneration")

        if not isinstance(titles, list):
            raise ValueError("Expected a JSON array of title objects")

        self.logger.info("Generated %d titles", len(titles))
        return titles

    @retry(max_attempts=3, base_delay=2.0, exceptions=(anthropic.APIError,))
    def generate_thumbnail_concepts(self, script: dict, count: int = 5) -> list[dict]:
        """Generate thumbnail concepts with text overlays and image prompts.

        Args:
            script: The video script dict.
            count: Number of thumbnail concepts to generate.

        Returns:
            List of dicts with keys: concept, image_prompt, primary_text,
            secondary_text, style.
        """
        self.logger.info("Generating %d thumbnail concepts", count)

        raw = self._call_claude(
            system=_THUMBNAIL_SYSTEM,
            user_message=(
                f"Generate exactly {count} YouTube thumbnail concepts for this script:\n\n"
                f"Title: {script.get('title', 'N/A')}\n"
                f"Description: {script.get('description', 'N/A')}\n"
                f"Hook: {script.get('hook', 'N/A')}\n"
                f"Tags: {', '.join(script.get('tags', []))}\n\n"
                f"Section headings:\n"
                + "\n".join(
                    f"  {s.get('section_number', i)}. {s.get('heading', '')}"
                    for i, s in enumerate(script.get("sections", []), 1)
                )
            ),
            max_tokens=4096,
        )

        concepts = self._parse_json(raw, context="ThumbnailGeneration")

        if not isinstance(concepts, list):
            raise ValueError("Expected a JSON array of thumbnail concept objects")

        self.logger.info("Generated %d thumbnail concepts", len(concepts))
        return concepts
