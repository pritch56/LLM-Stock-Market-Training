import logging
from dataclasses import dataclass
from typing import Optional

from cleaners.deduplicator import Deduplicator, content_hash
from cleaners.html_cleaner import extract_text
from cleaners.text_normalizer import normalise
from config.settings import settings
from scraper.base import ScrapeResult

logger = logging.getLogger(__name__)


@dataclass
class CleanedDocument:
    url: str
    source_name: str
    clean_text: str
    word_count: int
    content_hash: str
    tags: list[str]
    raw_id: Optional[int] = None


def clean_result(result: ScrapeResult, selector: Optional[str], dedup: Deduplicator) -> Optional[CleanedDocument]:
    if not result.success:
        return None

    text = extract_text(result.html, selector)
    text = normalise(text)

    word_count = len(text.split())
    if word_count < settings.min_input_text_length // 5:
        logger.debug("Skipping %s: too short (%d words)", result.url, word_count)
        return None

    if dedup.is_duplicate(text):
        logger.debug("Skipping %s: duplicate content", result.url)
        return None

    return CleanedDocument(
        url=result.url,
        source_name=result.source_name,
        clean_text=text,
        word_count=word_count,
        content_hash=content_hash(text),
        tags=result.tags,
    )
