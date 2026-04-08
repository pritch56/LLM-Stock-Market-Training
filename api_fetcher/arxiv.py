"""
arXiv paper abstracts via the public Atom API.
No API key required.
"""
import asyncio
import logging
import xml.etree.ElementTree as ET

import httpx

from scraper.base import ScrapeResult

logger = logging.getLogger(__name__)

_arxiv_lock = asyncio.Lock()

_API_URL = "http://export.arxiv.org/api/query"
_ARXIV_DELAY = 3.0  # arXiv asks for >=3 s between requests
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


async def fetch(
    client: httpx.AsyncClient,
    source_name: str,
    query: str,
    max_results: int,
    tags: list[str],
) -> list[ScrapeResult]:
    async with _arxiv_lock:
        try:
            resp = await client.get(
                _API_URL,
                params={
                    "search_query": f"all:{query}",
                    "max_results": max_results,
                    "sortBy": "relevance",
                },
                timeout=60.0,
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.error("arXiv fetch failed for %r: %s", query, exc)
            return []
        finally:
            await asyncio.sleep(_ARXIV_DELAY)

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as exc:
        logger.error("arXiv XML parse error: %s", exc)
        return []

    results = []
    for entry in root.findall("atom:entry", _NS):
        title_el = entry.find("atom:title", _NS)
        summary_el = entry.find("atom:summary", _NS)
        id_el = entry.find("atom:id", _NS)
        authors = [
            a.findtext("atom:name", "", _NS)
            for a in entry.findall("atom:author", _NS)
        ]

        title = (title_el.text or "").strip().replace("\n", " ")
        summary = (summary_el.text or "").strip().replace("\n", " ")
        url = (id_el.text or "").strip()

        body = f"Title: {title}\n\nAuthors: {', '.join(authors)}\n\nAbstract: {summary}"

        if len(body.split()) < 30:
            continue

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
