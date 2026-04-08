"""
Pipeline: scrape article -> analyse with LLM -> store in PostgreSQL

Usage:
    python run_pipeline.py <article_url>
"""
import asyncio
import logging
import argparse

from database.db import init_db
from database.persistence import insert_article, insert_company_impacts
from llm_generation.client import build_client
from llm_generation.generator import analyze_article_with_llm
from scraper.scraper import scrape_article

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def run(url: str) -> None:
    init_db()

    logger.info("Scraping article from %s", url)
    article = await scrape_article(url)

    if not article.article_text.strip():
        logger.error("No article text extracted from %s", url)
        return

    logger.info("Analysing article with LLM")
    client = build_client()
    companies = await analyze_article_with_llm(client, article.article_text)

    article_id = insert_article(article.article_text, article.published_time)
    logger.info("Inserted article with id %d", article_id)

    if companies:
        insert_company_impacts(article_id, companies)
    else:
        logger.info("No companies identified in article")

    logger.info("Pipeline complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="News article stock impact pipeline")
    parser.add_argument("url", help="URL of the news article to process")
    args = parser.parse_args()
    asyncio.run(run(args.url))


if __name__ == "__main__":
    main()
