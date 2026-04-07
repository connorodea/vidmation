"""Blog URL scraper — extract article content from any URL."""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class BlogScraper:
    """Scrape and extract structured content from a blog URL.

    Uses httpx to fetch the page, then extracts title, text content,
    headings, and metadata using a lightweight HTML parser approach
    (no heavy dependencies like BeautifulSoup required).
    """

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    def scrape(self, url: str) -> dict[str, Any]:
        """Fetch and parse a blog URL into structured content.

        Args:
            url: The blog post URL to scrape.

        Returns:
            A dict with keys:
            - ``url``: The original URL
            - ``title``: The page/article title
            - ``headings``: List of heading strings (h1-h3)
            - ``paragraphs``: List of paragraph text strings
            - ``full_text``: All text content joined
            - ``word_count``: Approximate word count
            - ``meta_description``: Meta description if available
        """
        logger.info("Scraping blog URL: %s", url)

        html = self._fetch(url)
        result = self._parse_html(html)
        result["url"] = url

        logger.info(
            "Scraped: title=%r, %d paragraphs, %d words",
            result["title"],
            len(result["paragraphs"]),
            result["word_count"],
        )
        return result

    def _fetch(self, url: str) -> str:
        """Fetch the HTML content from a URL."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
        }

        with httpx.Client(timeout=self._timeout, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.text

    def _parse_html(self, html: str) -> dict[str, Any]:
        """Parse HTML and extract structured content.

        Uses regex-based extraction — lightweight and dependency-free.
        """
        # Extract title
        title = self._extract_first(html, r"<title[^>]*>(.*?)</title>") or ""
        title = self._clean_text(title)

        # Try og:title as fallback
        og_title = self._extract_first(
            html, r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']*)["\']'
        )
        if og_title and len(og_title) > len(title):
            title = self._clean_text(og_title)

        # Meta description
        meta_desc = self._extract_first(
            html, r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']'
        ) or ""
        meta_desc = self._clean_text(meta_desc)

        # Extract headings (h1-h3)
        headings: list[str] = []
        for tag in ["h1", "h2", "h3"]:
            pattern = rf"<{tag}[^>]*>(.*?)</{tag}>"
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            for m in matches:
                text = self._strip_tags(m).strip()
                if text and len(text) > 3:
                    headings.append(text)

        # Extract paragraphs
        paragraphs: list[str] = []
        p_matches = re.findall(r"<p[^>]*>(.*?)</p>", html, re.DOTALL | re.IGNORECASE)
        for p in p_matches:
            text = self._strip_tags(p).strip()
            # Filter out very short paragraphs (likely nav/footer elements)
            if text and len(text) > 30:
                paragraphs.append(text)

        # Also try to extract from article/main tags for better content
        article_html = self._extract_first(
            html, r"<article[^>]*>(.*?)</article>"
        ) or self._extract_first(
            html, r'<main[^>]*>(.*?)</main>'
        ) or self._extract_first(
            html, r'<div[^>]*class=["\'][^"\']*(?:post|article|content|entry)[^"\']*["\'][^>]*>(.*?)</div>'
        )

        if article_html:
            article_paras = re.findall(r"<p[^>]*>(.*?)</p>", article_html, re.DOTALL | re.IGNORECASE)
            article_texts = [self._strip_tags(p).strip() for p in article_paras if len(self._strip_tags(p).strip()) > 30]
            if len(article_texts) > len(paragraphs):
                paragraphs = article_texts

        # Extract list items as additional content
        li_matches = re.findall(r"<li[^>]*>(.*?)</li>", html, re.DOTALL | re.IGNORECASE)
        list_items: list[str] = []
        for li in li_matches:
            text = self._strip_tags(li).strip()
            if text and len(text) > 20:
                list_items.append(text)

        full_text = "\n\n".join(paragraphs)
        word_count = len(full_text.split())

        return {
            "title": title,
            "headings": headings,
            "paragraphs": paragraphs,
            "list_items": list_items,
            "full_text": full_text,
            "word_count": word_count,
            "meta_description": meta_desc,
        }

    @staticmethod
    def _extract_first(html: str, pattern: str) -> str | None:
        """Extract the first regex match from HTML."""
        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        return match.group(1) if match else None

    @staticmethod
    def _strip_tags(html: str) -> str:
        """Remove HTML tags from a string."""
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean extracted text — decode entities, normalize whitespace."""
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')
        text = text.replace("&#39;", "'")
        text = text.replace("&nbsp;", " ")
        text = re.sub(r"&#\d+;", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
