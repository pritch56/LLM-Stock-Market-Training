import asyncio
import json
import logging
from dataclasses import dataclass, field

from cleaners.pipeline import CleanedDocument
from config.settings import settings
from llm_generation.client import LLMClient
from llm_generation.prompt_builder import (
    SYSTEM_PROMPT,
    build_entity_prompt,
    build_generation_prompt,
)

logger = logging.getLogger(__name__)


@dataclass
class RawPair:
    instruction: str
    input: str
    output: str
    model_used: str
    prompt_tokens: int
    output_tokens: int
    document_id: int = 0
    source_tags: list[str] = field(default_factory=list)
    tickers: list[dict] = field(default_factory=list)  # [{name, ticker, exchange}]


async def _extract_entities(client: LLMClient, doc: CleanedDocument) -> list[dict]:
    prompt = build_entity_prompt(doc.clean_text)
    try:
        text, _, _ = await client.complete(prompt, system=SYSTEM_PROMPT)
        data = json.loads(text)
        entities = data.get("entities", [])
        if entities:
            tickers = [e["ticker"] for e in entities if e.get("ticker")]
            logger.info(
                "Extracted %d entities from %s: %s",
                len(entities),
                doc.source_name,
                ", ".join(tickers) if tickers else "no public tickers",
            )
        return entities
    except Exception as exc:
        logger.warning("Entity extraction failed for %s: %s", doc.url, exc)
        return []


async def _generate_for_document(
    client: LLMClient,
    doc: CleanedDocument,
    n: int,
) -> list[RawPair]:
    entities = await _extract_entities(client, doc)

    prompt = build_generation_prompt(doc.clean_text, n, entities=entities)
    try:
        text, pt, ot = await client.complete(prompt, system=SYSTEM_PROMPT)
    except Exception as exc:
        logger.error("LLM call failed for %s: %s", doc.url, exc)
        return []

    try:
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError("Expected a JSON array")
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Failed to parse LLM response for %s: %s", doc.url, exc)
        return []

    ticker_summary = [
        {"name": e.get("name"), "ticker": e.get("ticker"), "exchange": e.get("exchange")}
        for e in entities
        if e.get("ticker")
    ]

    pairs = []
    for item in data:
        if not all(k in item for k in ("instruction", "output")):
            continue
        pairs.append(
            RawPair(
                instruction=item["instruction"].strip(),
                input=item.get("input", "").strip(),
                output=item["output"].strip(),
                model_used=settings.llm_model,
                prompt_tokens=pt,
                output_tokens=ot,
                document_id=doc.raw_id or 0,
                source_tags=doc.tags,
                tickers=ticker_summary,
            )
        )
    return pairs


async def generate_pairs(
    client: LLMClient,
    documents: list[CleanedDocument],
) -> list[RawPair]:
    semaphore = asyncio.Semaphore(settings.generation_concurrency)

    async def bounded(doc: CleanedDocument) -> list[RawPair]:
        async with semaphore:
            return await _generate_for_document(client, doc, settings.pairs_per_document)

    nested = await asyncio.gather(*[bounded(d) for d in documents])
    return [pair for batch in nested for pair in batch]
