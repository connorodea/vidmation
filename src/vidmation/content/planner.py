"""AI-powered content planning and scheduling."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Any

import anthropic

from vidmation.config.profiles import ChannelProfile, get_default_profile, load_profile
from vidmation.config.settings import Settings, get_settings
from vidmation.db.engine import get_session
from vidmation.db.repos import ChannelRepo, VideoRepo
from vidmation.utils.retry import retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_CALENDAR_SYSTEM = """\
You are a YouTube content strategist.  You create data-driven content \
calendars that maximise audience growth, engagement, and channel authority.

Guidelines:
- Balance content pillars (education, entertainment, trending, evergreen).
- Vary formats (listicle, tutorial, explainer, story, comparison, reaction).
- Consider seasonal relevance and trending topics.
- Maintain a sustainable posting cadence.
- Mix high-effort "pillar" videos with lower-effort "bridge" videos.
- Never repeat the same topic in a 4-week span.

Return **strict JSON** — an array of calendar entries, no markdown fences.
"""

_CALENDAR_USER = """\
Create a {weeks}-week content calendar for a YouTube channel.

Channel: {channel_name}
Niche: {niche}
Tone: {tone}
Typical topics: {typical_topics}
Target audience: {target_audience}
Posting frequency: {frequency} videos per week
Start date: {start_date}
Existing topics to avoid repeating: {existing_topics}

Return a JSON array:
[
  {{
    "date": "YYYY-MM-DD",
    "topic": "...",
    "title": "...",
    "format": "listicle|tutorial|explainer|story|comparison|reaction|compilation",
    "content_type": "pillar|bridge|trending|evergreen|seasonal",
    "keywords": ["..."],
    "priority": "high|medium|low",
    "notes": "..."
  }}
]

Sort by date ascending.
"""

_GAPS_SYSTEM = """\
You are a YouTube content gap analyst.  Given a list of existing video \
topics for a channel, identify untapped topics, underserved angles, and \
areas where the channel could expand.

Return **strict JSON** with keys: covered_topics (list), gaps (list of \
objects with topic + reason), recommendations (list of strings).
No markdown fences.
"""

_GAPS_USER = """\
Analyse content gaps for this channel:

Channel: {channel_name}
Niche: {niche}
Target audience: {target_audience}
Existing video topics:
{existing_topics}

Identify 10-15 untapped topics and 5-8 actionable recommendations.
"""

_SERIES_SYSTEM = """\
You are a YouTube series strategist.  Suggest multi-episode video series \
ideas that build audience habit and encourage binge-watching.

Return **strict JSON** — an array of series objects.  No markdown fences.
"""

_SERIES_USER = """\
Suggest video series ideas for this channel:

Channel: {channel_name}
Niche: {niche}
Target audience: {target_audience}
Existing topics: {existing_topics}

For each series provide:
[
  {{
    "series_name": "...",
    "description": "...",
    "episode_count": <int>,
    "topics": ["Episode 1 topic", "Episode 2 topic", ...]
  }}
]

Suggest 3-5 series.
"""

_TRENDING_SYSTEM = """\
You are a YouTube trend analyst.  Identify timely, trending topics in a \
given niche that have high search potential and are suitable for faceless \
video content.

Return **strict JSON** — an array of topic objects.  No markdown fences.
"""

_TRENDING_USER = """\
Identify {count} trending or timely topics in the "{niche}" niche.

For each topic:
[
  {{
    "topic": "...",
    "relevance_score": 0.0-1.0,
    "timeliness": "evergreen|trending_now|seasonal|upcoming",
    "competition": "low|medium|high",
    "suggested_title": "...",
    "reason": "..."
  }}
]

Sort by relevance_score descending.
"""

_REPURPOSE_SYSTEM = """\
You are a content repurposing strategist.  Given an existing video's script, \
suggest ways to repurpose it into new content pieces to maximise ROI.

Return **strict JSON** — an array of repurpose suggestions.  No markdown fences.
"""

_REPURPOSE_USER = """\
Suggest repurposing ideas for this video:

Title: {title}
Description: {description}
Sections: {sections_summary}
Duration: {duration}s

For each suggestion:
[
  {{
    "type": "short|compilation|reaction|update|blog|carousel|thread|infographic",
    "description": "...",
    "potential": "high|medium|low",
    "effort": "low|medium|high",
    "notes": "..."
  }}
]
"""


class ContentPlanner:
    """AI-powered content planning and scheduling."""

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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @retry(max_attempts=3, base_delay=2.0, exceptions=(anthropic.APIError,))
    def _ask_claude(self, system: str, user: str) -> str:
        response = self._client.messages.create(
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text.strip()

    def _parse_json(self, raw: str) -> Any:
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

    def _resolve_channel(self, channel_name: str) -> tuple[Any, ChannelProfile]:
        """Look up a channel record and its profile.

        Returns (channel_record_or_None, profile).
        """
        session = get_session()
        try:
            repo = ChannelRepo(session)
            channel = repo.get_by_name(channel_name)
            if channel is None:
                return None, get_default_profile()
            try:
                profile = load_profile(channel.profile_path)
            except FileNotFoundError:
                profile = get_default_profile()
            return channel, profile
        finally:
            session.close()

    def _get_existing_topics(self, channel_name: str, limit: int = 100) -> list[str]:
        """Fetch existing video topics for de-duplication."""
        session = get_session()
        try:
            channel_repo = ChannelRepo(session)
            ch = channel_repo.get_by_name(channel_name)
            if ch is None:
                return []
            video_repo = VideoRepo(session)
            videos = video_repo.list_all(limit=limit)
            return [
                v.title or v.topic_prompt
                for v in videos
                if v.channel_id == ch.id
            ]
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_content_calendar(
        self,
        channel_name: str,
        weeks: int = 4,
        videos_per_week: int = 3,
    ) -> list[dict]:
        """Generate a content calendar for *weeks* weeks.

        Args:
            channel_name: Name of the channel in the database.
            weeks: Number of weeks to plan.
            videos_per_week: Target posting frequency.

        Returns:
            A list of calendar entry dicts sorted by date:
            ``[{date, topic, title, format, content_type, keywords, priority}]``
        """
        channel, profile = self._resolve_channel(channel_name)
        existing = self._get_existing_topics(channel_name)

        start = date.today()
        logger.info(
            "Generating %d-week calendar for %r (%d/week, starting %s)",
            weeks,
            channel_name,
            videos_per_week,
            start.isoformat(),
        )

        raw = self._ask_claude(
            system=_CALENDAR_SYSTEM,
            user=_CALENDAR_USER.format(
                weeks=weeks,
                channel_name=channel_name,
                niche=profile.niche,
                tone=profile.content.tone,
                typical_topics=", ".join(profile.content.typical_topics) or "general",
                target_audience=profile.target_audience,
                frequency=videos_per_week,
                start_date=start.isoformat(),
                existing_topics="; ".join(existing[:30]) or "None yet",
            ),
        )

        calendar: list[dict] = self._parse_json(raw)

        # Normalise dates
        for entry in calendar:
            if isinstance(entry.get("date"), str):
                try:
                    datetime.strptime(entry["date"], "%Y-%m-%d")
                except ValueError:
                    entry["date"] = start.isoformat()

        calendar.sort(key=lambda e: e.get("date", ""))
        logger.info("Generated calendar with %d entries", len(calendar))
        return calendar

    def analyze_content_gaps(self, channel_name: str) -> dict:
        """Analyse existing videos to find untapped topics.

        Returns:
            ``{covered_topics, gaps, recommendations}``
        """
        channel, profile = self._resolve_channel(channel_name)
        existing = self._get_existing_topics(channel_name)

        if not existing:
            return {
                "covered_topics": [],
                "gaps": [{"topic": "Everything", "reason": "No videos published yet"}],
                "recommendations": ["Start with introductory content in your niche"],
            }

        logger.info("Analysing content gaps for %r (%d existing)", channel_name, len(existing))

        raw = self._ask_claude(
            system=_GAPS_SYSTEM,
            user=_GAPS_USER.format(
                channel_name=channel_name,
                niche=profile.niche,
                target_audience=profile.target_audience,
                existing_topics="\n".join(f"- {t}" for t in existing),
            ),
        )
        return self._parse_json(raw)

    def suggest_series(self, channel_name: str) -> list[dict]:
        """Suggest video series ideas for the channel.

        Returns:
            ``[{series_name, description, episode_count, topics}]``
        """
        channel, profile = self._resolve_channel(channel_name)
        existing = self._get_existing_topics(channel_name)

        logger.info("Generating series suggestions for %r", channel_name)

        raw = self._ask_claude(
            system=_SERIES_SYSTEM,
            user=_SERIES_USER.format(
                channel_name=channel_name,
                niche=profile.niche,
                target_audience=profile.target_audience,
                existing_topics=", ".join(existing[:20]) or "None yet",
            ),
        )
        return self._parse_json(raw)

    def trending_topics(self, niche: str, count: int = 20) -> list[dict]:
        """Identify trending topics in a niche.

        Args:
            niche: Content niche to analyse.
            count: Number of topics to return (max 30).

        Returns:
            ``[{topic, relevance_score, timeliness, competition}]``
        """
        count = max(5, min(count, 30))
        logger.info("Finding %d trending topics in niche=%r", count, niche)

        raw = self._ask_claude(
            system=_TRENDING_SYSTEM,
            user=_TRENDING_USER.format(count=count, niche=niche),
        )

        topics: list[dict] = self._parse_json(raw)
        topics.sort(key=lambda t: t.get("relevance_score", 0), reverse=True)
        return topics[:count]

    def repurpose_suggestions(self, video_id: str) -> list[dict]:
        """Suggest repurposing ideas for existing content.

        Args:
            video_id: ID of the video to repurpose.

        Returns:
            ``[{type, description, potential, effort, notes}]``
        """
        session = get_session()
        try:
            video_repo = VideoRepo(session)
            video = video_repo.get(video_id)
            if video is None:
                raise ValueError(f"Video '{video_id}' not found")

            script = video.script_json or {}
            sections_summary = "; ".join(
                s.get("heading", "")
                for s in script.get("sections", [])
            )
        finally:
            session.close()

        logger.info("Generating repurpose suggestions for video %s", video_id)

        raw = self._ask_claude(
            system=_REPURPOSE_SYSTEM,
            user=_REPURPOSE_USER.format(
                title=video.title or script.get("title", ""),
                description=script.get("description", video.description or ""),
                sections_summary=sections_summary or "N/A",
                duration=video.duration_seconds or script.get("total_estimated_duration_seconds", 0),
            ),
        )
        return self._parse_json(raw)
