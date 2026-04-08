"""
Pipeline: discover financial news articles -> scrape -> analyse with LLM -> store in SQLite

Usage:
    python run_pipeline.py            # auto-discover from RSS feeds
    python run_pipeline.py <url>      # process a single article
"""
import asyncio
import logging
import argparse

from config.settings import settings
from database.db import init_db
from database.persistence import insert_article, insert_company_impacts, url_already_processed
from llm_generation.client import build_client
from llm_generation.generator import analyze_article_with_llm
from scraper.discovery import discover_articles
from scraper.scraper import scrape_article

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def process_article(client, url: str) -> bool:
    if url_already_processed(url):
        logger.info("Skipping already-processed URL: %s", url)
        return False

    try:
        article = await scrape_article(url)
    except Exception as exc:
        logger.warning("Failed to scrape %s: %s", url, exc)
        return False

    if not article.article_text.strip():
        logger.warning("No article text extracted from %s", url)
        return False

    logger.info("Analysing article with LLM")
    companies = await analyze_article_with_llm(client, article.article_text)

    article_id = insert_article(article.article_text, article.published_time, source_url=url)
    logger.info("Inserted article with id %d", article_id)

    if companies:
        insert_company_impacts(article_id, companies)
    else:
        logger.info("No companies identified in article")

    return True


async def run(url: str | None = None) -> None:
    init_db()
    client = build_client()

    if url:
        await process_article(client, url)
    else:
        logger.info("Discovering articles from RSS feeds")
        discovered = await discover_articles(max_per_feed=settings.max_articles_per_feed)
        processed = 0
        for item in discovered:
            logger.info("Processing: %s", item.title or item.url)
            if await process_article(client, item.url):
                processed += 1
        logger.info("Pipeline complete. Processed %d new articles out of %d discovered.", processed, len(discovered))


def main() -> None:
    parser = argparse.ArgumentParser(description="News article stock impact pipeline")
    parser.add_argument("url", nargs="?", default=None, help="URL of a specific article (optional)")
    args = parser.parse_args()
    asyncio.run(run(args.url))


if __name__ == "__main__":
    main()
