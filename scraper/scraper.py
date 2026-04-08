import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup

from scraper.base import fetch_url

logger = logging.getLogger(__name__)

_NOISE_TAGS = {
    "script", "style", "nav", "footer", "header", "aside",
    "form", "button", "iframe", "noscript", "svg", "figure",
}
_WHITESPACE_RE = re.compile(r"\n{3,}")
_INLINE_SPACE_RE = re.compile(r"[ \t]{2,}")


@dataclass
class ArticleData:
    article_text: str
    published_time: Optional[datetime]


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(_NOISE_TAGS):
        tag.decompose()
    root = soup.body or soup
    text = root.get_text(separator="\n")
    text = _INLINE_SPACE_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub("\n\n", text)
    return text.strip()


def _extract_published_time(html: str) -> Optional[datetime]:
    soup = BeautifulSoup(html, "lxml")

    # Check common meta tags for published time
    for attr in (
        {"property": "article:published_time"},
        {"name": "pubdate"},
        {"name": "date"},
        {"property": "og:article:published_time"},
        {"itemprop": "datePublished"},
    ):
        tag = soup.find("meta", attrs=attr)
        if tag and tag.get("content"):
            try:
                return datetime.fromisoformat(tag["content"].replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue

    # Check <time> elements
    time_tag = soup.find("time", attrs={"datetime": True})
    if time_tag:
        try:
            return datetime.fromisoformat(time_tag["datetime"].replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass

    return None


async def scrape_article(url: str) -> ArticleData:
    html, _ = await fetch_url(url)
    article_text = _extract_text(html)
    published_time = _extract_published_time(html)
    logger.info("Scraped article from %s (%d chars)", url, len(article_text))
    return ArticleData(article_text=article_text, published_time=published_time)
