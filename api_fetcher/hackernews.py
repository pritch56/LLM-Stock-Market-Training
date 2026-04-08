"""
HackerNews content via the Algolia search API.
No API key required. Returns story text for items that have body content.
"""
import logging
from typing import Optional

import httpx

from scraper.base import ScrapeResult

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
_ITEM_URL = "https://hn.algolia.com/api/v1/items/{}"


async def fetch(
    client: httpx.AsyncClient,
    source_name: str,
    query: str,
    max_results: int,
    tags: list[str],
) -> list[ScrapeResult]:
    try:
        resp = await client.get(
            _SEARCH_URL,
            params={"query": query, "tags": "story", "hitsPerPage": max_results * 2},
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
    except Exception as exc:
        logger.error("HackerNews search failed for %r: %s", query, exc)
        return []

    results = []
    for hit in hits:
        object_id = hit.get("objectID")
        title = hit.get("title", "").strip()
        story_text = hit.get("story_text") or ""
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}"

        # story_text is HTML; strip tags for plain text
        if story_text:
            import re
            story_text = re.sub(r"<[^>]+>", " ", story_text)
            story_text = re.sub(r"\s{2,}", " ", story_text).strip()

        # Fetch comments to bulk up short stories
        body = f"{title}\n\n{story_text}".strip() if story_text else title

        if len(body.split()) < 40:
            # Try fetching item comments for more content
            try:
                item_resp = await client.get(_ITEM_URL.format(object_id))
                item_resp.raise_for_status()
                item = item_resp.json()
                comments = _extract_comments(item, depth=1)
                body = f"{body}\n\n{comments}".strip()
            except Exception:
                pass

        if len(body.split()) < 40:
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
        if len(results) >= max_results:
            break

    return results


def _extract_comments(item: dict, depth: int) -> str:
    import re
    parts = []
    for child in item.get("children", [])[:5]:
        text = child.get("text") or ""
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s{2,}", " ", text).strip()
        if len(text.split()) > 10:
            parts.append(text)
        if depth > 0:
            parts.append(_extract_comments(child, depth - 1))
    return "\n".join(parts)
