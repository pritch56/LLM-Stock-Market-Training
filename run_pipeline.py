"""
Full pipeline: scrape -> clean -> generate -> filter -> export

Usage:
    python run_pipeline.py
    python run_pipeline.py --sources config/sources.yaml --output output/
"""
import asyncio
import logging
import argparse
from pathlib import Path

from config.settings import settings
from database.db import init_db
from database.persistence import save_pairs, save_processed, save_raw
from cleaners.deduplicator import Deduplicator
from cleaners.pipeline import clean_result
from dataset_builder.builder import build_records
from dataset_builder.exporter import export_all
from filters.pipeline import run_filters
from llm_generation.client import build_client
from llm_generation.generator import generate_pairs
from scraper.scraper import scrape_all
from scraper.sources import load_sources

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def run(sources_file: Path, output_dir: Path, mock: bool = False) -> None:
    init_db()

    logger.info("Loading sources from %s", sources_file)
    sources = load_sources(sources_file)
    logger.info("Scraping %d sources", len(sources))

    scrape_results = await scrape_all(sources)
    success = sum(1 for r in scrape_results if r.success)
    logger.info("Scraped %d/%d sources successfully", success, len(scrape_results))

    source_selector_map = {s.url: s.content_selector for s in sources}

    dedup = Deduplicator()
    cleaned_docs = []
    for result in scrape_results:
        save_raw(result)

        selector = source_selector_map.get(result.url)
        doc = clean_result(result, selector, dedup)
        if doc is None:
            continue

        doc_id = save_processed(doc)
        if doc_id:
            doc.raw_id = doc_id
            cleaned_docs.append(doc)

    logger.info("Cleaned %d documents", len(cleaned_docs))

    if not cleaned_docs:
        logger.warning("No documents to process; exiting")
        return

    provider = "mock" if mock else settings.llm_provider
    logger.info("Generating instruction pairs via %s", provider)
    client = build_client(mock=mock)
    raw_pairs = await generate_pairs(client, cleaned_docs)
    logger.info("Generated %d raw pairs", len(raw_pairs))

    filter_results = run_filters(raw_pairs)
    save_pairs(filter_results)

    records = build_records(filter_results)
    logger.info("Exporting %d final records to %s", len(records), output_dir)
    export_all(records, output_dir)
    logger.info("Pipeline complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM dataset generation pipeline")
    parser.add_argument(
        "--sources", type=Path, default=settings.sources_file,
        help="Path to sources YAML file",
    )
    parser.add_argument(
        "--output", type=Path, default=settings.output_dir,
        help="Output directory",
    )
    parser.add_argument(
        "--mock", action="store_true",
        help="Use mock LLM client (no API key required, for testing)",
    )
    args = parser.parse_args()
    asyncio.run(run(args.sources, args.output, mock=args.mock))


if __name__ == "__main__":
    main()
