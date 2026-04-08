import logging
from typing import Optional

from sqlalchemy.exc import IntegrityError

from cleaners.pipeline import CleanedDocument
from database.db import get_session
from database.models import InstructionPair, ProcessedDocument, RawDocument
from filters.pipeline import FilterResult
from scraper.base import ScrapeResult
from scraper.sources import SourceConfig

logger = logging.getLogger(__name__)


def save_raw(result: ScrapeResult) -> Optional[int]:
    with get_session() as session:
        existing = session.query(RawDocument).filter_by(url=result.url).first()
        if existing:
            return existing.id

        doc = RawDocument(
            url=result.url,
            source_name=result.source_name,
            raw_html=result.html,
            http_status=result.status_code,
            tags=result.tags,
        )
        session.add(doc)
        try:
            session.flush()
            return doc.id
        except IntegrityError:
            session.rollback()
            return None


def save_processed(doc: CleanedDocument) -> Optional[int]:
    with get_session() as session:
        existing = session.query(ProcessedDocument).filter_by(
            content_hash=doc.content_hash
        ).first()
        if existing:
            return existing.id

        raw = session.query(RawDocument).filter_by(url=doc.url).first()
        raw_id = raw.id if raw else None

        processed = ProcessedDocument(
            raw_id=raw_id,
            clean_text=doc.clean_text,
            word_count=doc.word_count,
            language="en",
            content_hash=doc.content_hash,
        )
        session.add(processed)
        try:
            session.flush()
            return processed.id
        except IntegrityError:
            session.rollback()
            return None


def save_pairs(results: list[FilterResult]) -> int:
    saved = 0
    with get_session() as session:
        for r in results:
            pair = InstructionPair(
                document_id=r.pair.document_id or None,
                instruction=r.pair.instruction,
                input=r.pair.input,
                output=r.pair.output,
                model_used=r.pair.model_used,
                generation_prompt_tokens=r.pair.prompt_tokens,
                generation_output_tokens=r.pair.output_tokens,
                passed_filters=r.passed,
                filter_reason=r.reason,
                tickers=r.pair.tickers,
                extra={"tags": r.pair.source_tags},
            )
            session.add(pair)
            if r.passed:
                saved += 1
    return saved
