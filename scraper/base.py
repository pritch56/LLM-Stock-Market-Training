import logging
from typing import Optional

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)


def _build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": settings.scrape_user_agent},
        timeout=settings.scrape_timeout_seconds,
        follow_redirects=True,
    )


async def fetch_url(url: str) -> tuple[str, int]:
    async with _build_client() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text, response.status_code
