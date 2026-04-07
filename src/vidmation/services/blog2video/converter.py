"""Blog-to-video converter — transform scraped blog content into a video script."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import openai

from vidmation.services.base import BaseService
from vidmation.services.blog2video.scraper import BlogScraper
from vidmation.utils.retry import retry

if TYPE_CHECKING:
    from vidmation.config.profiles import ChannelProfile
    from vidmation.config.settings import Settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a professional YouTube scriptwriter who specialises in converting \
written blog posts and articles into engaging, faceless YouTube video scripts.

You will receive the full text of a blog post. Your job is to:
1. Analyse the blog content and identify the key points, structure, and value.
2. Create a structured video script that covers the same content in an \
   engaging, conversational voiceover format.
3. Adapt the written content into spoken content — shorter sentences, \
   conversational tone, rhetorical questions, and emotional hooks.

Return **only** valid JSON matching this schema — no markdown fences, \
no extra text:

{schema}

Rules:
- The "hook" should grab attention in the first 5 seconds with a compelling \
  question or bold statement derived from the blog's main thesis.
- Each section's "narration" should be conversational and paced for \
  voice-over (~150 words/min). Convert written blog paragraphs into \
  spoken narration — don't just read the blog aloud.
- Keep sections focused on one key point each.
- "visual_query" must be a concise stock media search phrase.
- "visual_type": one of stock_video, stock_image, ai_image.
- "estimated_duration_seconds" per section reflects narration length.
- "tags": 8-15 relevant YouTube tags based on the blog topic.
- Create 5-8 sections depending on the blog length.
- Include a compelling outro with a call to action.
"""

_USER_TEMPLATE = """\
Convert this blog post into a YouTube video script:

**Blog Title:** {title}

**Blog URL:** {url}

**Blog Content:**
{content}

---

Channel profile:
- Niche: {niche}
- Tone: {tone}
- Target audience: {target_audience}
"""

_SCRIPT_SCHEMA = {
    "type": "object",
    "required": ["title", "description", "tags", "hook", "sections", "outro",
                 "total_estimated_duration_seconds"],
    "properties": {
        "title": {"type": "string", "description": "SEO-optimized video title"},
        "description": {"type": "string", "description": "YouTube description"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "hook": {"type": "string", "description": "Attention-grabbing opening line"},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["section_number", "heading", "narration",
                             "visual_query", "visual_type",
                             "estimated_duration_seconds"],
                "properties": {
                    "section_number": {"type": "integer"},
                    "heading": {"type": "string"},
                    "narration": {"type": "string"},
                    "visual_query": {"type": "string"},
                    "visual_type": {"type": "string"},
                    "estimated_duration_seconds": {"type": "integer"},
                },
            },
        },
        "outro": {"type": "string"},
        "total_estimated_duration_seconds": {"type": "integer"},
        "source_url": {"type": "string"},
    },
}


class BlogToVideoConverter(BaseService):
    """Convert blog post URLs into structured video scripts using AI.

    Workflow:
    1. Scrape the blog URL to extract content.
    2. Send the content to GPT-4o to generate a video script.
    3. Return the script in the same format as the normal script generator.
    """

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
        self._scraper = BlogScraper()

    def convert(
        self,
        url: str,
        channel_profile: ChannelProfile | None = None,
    ) -> dict[str, Any]:
        """Scrape a blog URL and generate a video script.

        Args:
            url: The blog post URL.
            channel_profile: Optional channel profile for tone/niche context.

        Returns:
            A structured video script dict (same format as ScriptGenerator).
        """
        self.logger.info("Blog-to-video: scraping %s", url)

        # Step 1: Scrape the blog
        blog_content = self._scraper.scrape(url)

        if blog_content["word_count"] < 50:
            raise ValueError(
                f"Blog content too short ({blog_content['word_count']} words). "
                "Could not extract enough content from the URL."
            )

        self.logger.info(
            "Blog scraped: %r (%d words, %d paragraphs)",
            blog_content["title"],
            blog_content["word_count"],
            len(blog_content["paragraphs"]),
        )

        # Step 2: Generate video script with AI
        script = self._generate_script(blog_content, channel_profile)

        # Add source URL reference
        script["source_url"] = url
        script["source_blog_title"] = blog_content["title"]

        self.logger.info(
            "Blog-to-video script: %r (%d sections, ~%ds)",
            script.get("title", "untitled"),
            len(script.get("sections", [])),
            script.get("total_estimated_duration_seconds", 0),
        )

        return script

    @retry(max_attempts=3, base_delay=2.0, exceptions=(openai.APIError,))
    def _generate_script(
        self,
        blog_content: dict[str, Any],
        channel_profile: ChannelProfile | None = None,
    ) -> dict[str, Any]:
        """Call GPT-4o to convert blog content into a video script."""
        from vidmation.config.profiles import get_default_profile

        profile = channel_profile or get_default_profile()

        # Truncate content if very long (GPT-4o context limit considerations)
        full_text = blog_content["full_text"]
        if len(full_text) > 15000:
            full_text = full_text[:15000] + "\n\n[Content truncated for length...]"

        # Include headings for structure hints
        headings_text = ""
        if blog_content.get("headings"):
            headings_text = "\n**Section headings found:**\n" + "\n".join(
                f"- {h}" for h in blog_content["headings"]
            )

        content_block = full_text + headings_text

        system = _SYSTEM_PROMPT.format(
            schema=json.dumps(_SCRIPT_SCHEMA, indent=2),
        )

        user_msg = _USER_TEMPLATE.format(
            title=blog_content["title"],
            url=blog_content.get("url", ""),
            content=content_block,
            niche=profile.niche,
            tone=profile.content.tone,
            target_audience=profile.target_audience,
        )

        self.logger.info("Calling GPT-4o to generate video script from blog...")

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
            self.logger.error("GPT-4o returned invalid JSON: %s", exc)
            raise ValueError("GPT-4o response was not valid JSON") from exc

        return script
