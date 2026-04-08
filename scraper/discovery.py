import logging
from dataclasses import dataclass
from typing import Optional

import feedparser
import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

FINANCIAL_RSS_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^DJI&region=US&lang=en-US",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",  # Top News
    "https://www.cnbc.com/id/10001147/device/rss/rss.html",   # Finance
    "https://feeds.marketwatch.com/marketwatch/topstories/",
    "https://feeds.marketwatch.com/marketwatch/marketpulse/",
]


@dataclass
class DiscoveredArticle:
    url: str
    title: Optional[str]


async def discover_articles(max_per_feed: int = 5) -> list[DiscoveredArticle]:
    articles: list[DiscoveredArticle] = []
    seen_urls: set[str] = set()

    async with httpx.AsyncClient(
        headers={"User-Agent": settings.scrape_user_agent},
        timeout=settings.scrape_timeout_seconds,
        follow_redirects=True,
    ) as client:
        for feed_url in FINANCIAL_RSS_FEEDS:
            try:
                resp = await client.get(feed_url)
                resp.raise_for_status()
                feed = feedparser.parse(resp.text)
                count = 0
                for entry in feed.entries:
                    link = entry.get("link")
                    if not link or link in seen_urls:
                        continue
                    seen_urls.add(link)
                    articles.append(DiscoveredArticle(
                        url=link,
                        title=entry.get("title"),
                    ))
                    count += 1
                    if count >= max_per_feed:
                        break
                logger.info("Discovered %d articles from %s", count, feed_url)
            except Exception as exc:
                logger.warning("Failed to fetch feed %s: %s", feed_url, exc)

    logger.info("Total discovered articles: %d", len(articles))
    return articles
