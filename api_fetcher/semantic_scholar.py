"""
Paper abstracts via the Semantic Scholar Graph API.
No API key required. 5000 requests / 5 minutes unauthenticated.
"""
import asyncio
import logging

import httpx

from scraper.base import ScrapeResult

logger = logging.getLogger(__name__)

_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_FIELDS = "title,authors,abstract,year,venue"


async def fetch(
    client: httpx.AsyncClient,
    source_name: str,
    query: str,
    max_results: int,
    tags: list[str],
) -> list[ScrapeResult]:
    for attempt in range(3):
        try:
            resp = await client.get(
                _API_URL,
                params={"query": query, "fields": _FIELDS, "limit": max_results},
                timeout=30.0,
            )
            if resp.status_code == 429:
                wait = 5 * (2 ** attempt)
                logger.warning("Semantic Scholar 429 for %r; retrying in %ds", query, wait)
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception as exc:
            logger.error("Semantic Scholar fetch failed for %r: %s", query, exc)
            return []
    else:
        logger.error("Semantic Scholar gave up after retries for %r", query)
        return []

    results = []
    for paper in data.get("data", []):
        title = (paper.get("title") or "").strip()
        abstract = (paper.get("abstract") or "").strip()
        year = paper.get("year") or ""
        venue = (paper.get("venue") or "").strip()
        authors = ", ".join(
            a.get("name", "") for a in (paper.get("authors") or [])
        )
        paper_id = paper.get("paperId", "")
        url = f"https://www.semanticscholar.org/paper/{paper_id}"

        if not abstract or len(abstract.split()) < 30:
            continue

        body = f"Title: {title}\n\nAuthors: {authors}\n\nVenue: {venue} ({year})\n\nAbstract: {abstract}"

        results.append(
            ScrapeResult(
                url=url,
                source_name=source_name,
                html=body,
                status_code=200,
                tags=tags,
                pre_cleaned=True,
            )
        )

    return results
