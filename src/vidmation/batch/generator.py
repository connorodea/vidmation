"""Batch video generator — queue multiple videos from topics, CSV, or RSS feeds."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import anthropic

from vidmation.batch.csv_parser import BatchCSVParser, BatchRow
from vidmation.config.profiles import ChannelProfile, get_default_profile, load_profile
from vidmation.config.settings import Settings, get_settings
from vidmation.db.engine import get_session, init_db
from vidmation.db.repos import ChannelRepo
from vidmation.models.job import Job, JobType
from vidmation.models.video import Video, VideoFormat
from vidmation.queue.tasks import enqueue_video
from vidmation.utils.retry import retry

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_TOPIC_IDEAS_SYSTEM = """\
You are a YouTube content strategist.  Given a channel profile, generate video \
topic ideas that will perform well for the channel's niche and audience.

Consider:
- Trending topics in the niche
- Evergreen content that consistently performs
- Content gaps — topics the audience wants but few creators cover
- Series potential — topics that naturally lead to follow-up videos
- SEO opportunity — topics with high search volume and low competition

Return **strict JSON** — an array of objects:
[
  {
    "topic": "<clear, specific topic title>",
    "angle": "<unique angle or hook>",
    "content_type": "listicle|explainer|story|comparison|tutorial|opinion",
    "estimated_interest": <0.0-1.0>,
    "reasoning": "<why this topic would perform well>"
  }
]
"""


class BatchVideoGenerator:
    """Generate multiple videos from a list of topics, CSV file, or RSS feed.

    This is the primary entry point for batch operations.  Each method
    validates input, resolves the channel, and enqueues individual video
    jobs via :func:`vidmation.queue.tasks.enqueue_video`.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.logger = logging.getLogger("vidmation.batch.BatchVideoGenerator")

    # ------------------------------------------------------------------
    # Channel resolution helpers
    # ------------------------------------------------------------------

    def _resolve_channel(self, channel_name: str) -> Any:
        """Look up a channel by name and return the DB record.

        Raises:
            ValueError: If the channel does not exist.
        """
        init_db()
        session = get_session()
        try:
            repo = ChannelRepo(session)
            channel = repo.get_by_name(channel_name)
            if channel is None:
                raise ValueError(
                    f"Channel '{channel_name}' not found. "
                    f"Create it first with: vidmation channel add --name '{channel_name}'"
                )
            return channel
        finally:
            session.close()

    def _resolve_profile(self, channel_name: str) -> ChannelProfile:
        """Load the ChannelProfile for a channel name."""
        init_db()
        session = get_session()
        try:
            repo = ChannelRepo(session)
            ch = repo.get_by_name(channel_name)
            if ch is None:
                return get_default_profile()
            try:
                return load_profile(ch.profile_path)
            except (FileNotFoundError, AttributeError):
                return get_default_profile()
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def from_topics(
        self,
        topics: list[str],
        channel_name: str,
        format: str = "landscape",
    ) -> list[tuple[Video, Job]]:
        """Queue multiple videos from a list of topic strings.

        Args:
            topics: List of video topic prompts.
            channel_name: Name of the channel to use.
            format: Video format (landscape, portrait, short).

        Returns:
            List of ``(Video, Job)`` tuples for each queued video.
        """
        if not topics:
            raise ValueError("At least one topic is required")

        self._resolve_channel(channel_name)  # Validate channel exists

        results: list[tuple[Video, Job]] = []
        failed: list[tuple[str, str]] = []

        for i, topic in enumerate(topics, 1):
            topic = topic.strip()
            if not topic:
                self.logger.warning("Skipping empty topic at position %d", i)
                continue

            try:
                video, job = enqueue_video(
                    topic=topic,
                    channel_name=channel_name,
                    format=format,
                    job_type=JobType.FULL_PIPELINE,
                )
                results.append((video, job))
                self.logger.info(
                    "Queued [%d/%d] topic=%r, video_id=%s, job_id=%s",
                    i,
                    len(topics),
                    topic,
                    video.id,
                    job.id,
                )
            except Exception as exc:
                self.logger.error("Failed to queue topic=%r: %s", topic, exc)
                failed.append((topic, str(exc)))

        if failed:
            self.logger.warning(
                "%d of %d topics failed to queue: %s",
                len(failed),
                len(topics),
                ", ".join(t for t, _ in failed),
            )

        self.logger.info(
            "Batch complete: %d queued, %d failed, %d total",
            len(results),
            len(failed),
            len(topics),
        )
        return results

    def from_csv(
        self,
        csv_path: Path,
        channel_name: str,
    ) -> list[tuple[Video, Job]]:
        """Queue videos from a CSV file.

        Expected CSV columns: topic (required), title, format, tags,
        schedule_date, priority, notes.

        Args:
            csv_path: Path to the CSV file.
            channel_name: Name of the channel to use.

        Returns:
            List of ``(Video, Job)`` tuples.
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        self._resolve_channel(channel_name)

        parser = BatchCSVParser()
        rows = parser.parse(csv_path)

        if not rows:
            raise ValueError(f"No valid rows found in {csv_path}")

        self.logger.info("Parsed %d rows from %s", len(rows), csv_path)

        results: list[tuple[Video, Job]] = []
        failed: list[tuple[str, str]] = []

        for i, row in enumerate(rows, 1):
            try:
                video_format = row.format or "landscape"
                video, job = enqueue_video(
                    topic=row.topic,
                    channel_name=channel_name,
                    format=video_format,
                    job_type=JobType.FULL_PIPELINE,
                )
                results.append((video, job))
                self.logger.info(
                    "Queued CSV row [%d/%d] topic=%r, format=%s",
                    i,
                    len(rows),
                    row.topic,
                    video_format,
                )
            except Exception as exc:
                self.logger.error("Failed to queue CSV row %d (%r): %s", i, row.topic, exc)
                failed.append((row.topic, str(exc)))

        self.logger.info(
            "CSV batch complete: %d queued, %d failed from %s",
            len(results),
            len(failed),
            csv_path,
        )
        return results

    def from_rss(
        self,
        feed_url: str,
        channel_name: str,
        max_items: int = 10,
    ) -> list[tuple[Video, Job]]:
        """Generate videos from an RSS/blog feed — repurpose existing content.

        Fetches the feed, extracts titles and summaries, and queues each as
        a video topic.

        Args:
            feed_url: URL of the RSS/Atom feed.
            channel_name: Name of the channel to use.
            max_items: Maximum number of feed items to process.

        Returns:
            List of ``(Video, Job)`` tuples.
        """
        try:
            import feedparser
        except ImportError as exc:
            raise ImportError(
                "RSS batch generation requires the 'feedparser' package. "
                "Install it with: pip install feedparser"
            ) from exc

        self.logger.info("Fetching RSS feed: %s (max %d items)", feed_url, max_items)

        feed = feedparser.parse(feed_url)

        if feed.bozo and not feed.entries:
            raise ValueError(
                f"Failed to parse RSS feed: {feed.bozo_exception}"
            )

        entries = feed.entries[:max_items]
        if not entries:
            raise ValueError(f"No entries found in feed: {feed_url}")

        topics: list[str] = []
        for entry in entries:
            title = entry.get("title", "").strip()
            summary = entry.get("summary", "").strip()
            if title:
                # Combine title and summary for a richer topic prompt.
                if summary:
                    topic = f"{title} — {summary[:200]}"
                else:
                    topic = title
                topics.append(topic)

        self.logger.info("Extracted %d topics from RSS feed", len(topics))
        return self.from_topics(topics=topics, channel_name=channel_name)

    @retry(max_attempts=3, base_delay=2.0, exceptions=(anthropic.APIError,))
    def generate_topic_ideas(
        self,
        channel_name: str,
        count: int = 20,
    ) -> list[dict]:
        """Use AI to generate topic ideas based on channel profile.

        Analyzes the channel's niche, audience, and content style to suggest
        topics that are likely to perform well.

        Args:
            channel_name: Name of the channel.
            count: Number of topic ideas to generate.

        Returns:
            List of dicts with keys: topic, angle, content_type,
            estimated_interest, reasoning.
        """
        profile = self._resolve_profile(channel_name)

        self.logger.info(
            "Generating %d topic ideas for channel=%r (niche=%r)",
            count,
            channel_name,
            profile.niche,
        )

        api_key = self.settings.anthropic_api_key.get_secret_value()
        if not api_key:
            raise ValueError(
                "anthropic_api_key is required for topic generation. "
                "Set VIDMATION_ANTHROPIC_API_KEY in your environment."
            )

        client = anthropic.Anthropic(api_key=api_key)

        user_message = (
            f"Generate exactly {count} video topic ideas for this channel:\n\n"
            f"**Channel:** {profile.name}\n"
            f"**Niche:** {profile.niche}\n"
            f"**Target audience:** {profile.target_audience}\n"
            f"**Tone:** {profile.content.tone}\n"
            f"**Script style:** {profile.content.script_style}\n"
            f"**Typical topics:** {', '.join(profile.content.typical_topics) or 'general'}\n\n"
            f"Focus on topics that will get views and engagement for this "
            f"specific niche and audience."
        )

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=_TOPIC_IDEAS_SYSTEM,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]

        try:
            ideas: list[dict] = json.loads(raw.strip())
        except json.JSONDecodeError as exc:
            self.logger.error("Claude returned invalid JSON for topic ideas: %s", exc)
            raise ValueError("Topic ideas response was not valid JSON") from exc

        if not isinstance(ideas, list):
            raise ValueError("Expected a JSON array of topic idea objects")

        self.logger.info("Generated %d topic ideas", len(ideas))
        return ideas
