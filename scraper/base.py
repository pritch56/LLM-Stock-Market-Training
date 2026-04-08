import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class ScrapeResult:
    url: str
    source_name: str
    html: Optional[str]
    status_code: int
    tags: list[str] = field(default_factory=list)
    error: Optional[str] = None
    pre_cleaned: bool = False  # True when content is already plain text (API sources)

    @property
    def success(self) -> bool:
        return self.html is not None and self.status_code == 200


def _build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": settings.scrape_user_agent},
        timeout=settings.scrape_timeout_seconds,
        follow_redirects=True,
    )


class RateLimiter:
    def __init__(self, delay: float):
        self._delay = delay
        self._lock = asyncio.Lock()
        self._last_call: float = 0.0

    async def acquire(self) -> None:
        async with self._lock:
            now = asyncio.get_event_loop().time()
            wait = self._delay - (now - self._last_call)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = asyncio.get_event_loop().time()


_rate_limiter = RateLimiter(settings.scrape_delay_seconds)


@retry(
    retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
    stop=stop_after_attempt(settings.scrape_max_retries),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
async def fetch_url(client: httpx.AsyncClient, url: str) -> tuple[str, int]:
    await _rate_limiter.acquire()
    response = await client.get(url)
    response.raise_for_status()
    return response.text, response.status_code
