import asyncio
import logging

import httpx
from playwright.async_api import async_playwright, Browser

from config.settings import settings
from scraper.base import ScrapeResult, _build_client, fetch_url
from scraper.sources import SourceConfig

logger = logging.getLogger(__name__)


async def _scrape_static(client: httpx.AsyncClient, source: SourceConfig) -> ScrapeResult:
    try:
        html, status = await fetch_url(client, source.url)
        return ScrapeResult(
            url=source.url,
            source_name=source.name,
            html=html,
            status_code=status,
            tags=source.tags,
        )
    except Exception as exc:
        logger.warning("Failed to scrape %s: %s", source.url, exc)
        return ScrapeResult(
            url=source.url,
            source_name=source.name,
            html=None,
            status_code=0,
            tags=source.tags,
            error=str(exc),
        )


async def _scrape_dynamic(browser: Browser, source: SourceConfig) -> ScrapeResult:
    page = await browser.new_page()
    try:
        await page.set_extra_http_headers({"User-Agent": settings.scrape_user_agent})
        response = await page.goto(source.url, timeout=settings.scrape_timeout_seconds * 1000)
        await page.wait_for_load_state("networkidle")
        html = await page.content()
        status = response.status if response else 0
        return ScrapeResult(
            url=source.url,
            source_name=source.name,
            html=html,
            status_code=status,
            tags=source.tags,
        )
    except Exception as exc:
        logger.warning("Playwright failed for %s: %s", source.url, exc)
        return ScrapeResult(
            url=source.url,
            source_name=source.name,
            html=None,
            status_code=0,
            tags=source.tags,
            error=str(exc),
        )
    finally:
        await page.close()


async def _fetch_api(client: httpx.AsyncClient, source: SourceConfig) -> list[ScrapeResult]:
    if source.fetcher == "hackernews":
        from api_fetcher.hackernews import fetch
    elif source.fetcher == "arxiv":
        from api_fetcher.arxiv import fetch
    elif source.fetcher == "semantic_scholar":
        from api_fetcher.semantic_scholar import fetch
    else:
        logger.error("Unknown API fetcher %r for source %r", source.fetcher, source.name)
        return []

    return await fetch(
        client=client,
        source_name=source.name,
        query=source.query or source.name,
        max_results=source.max_results,
        tags=source.tags,
    )


async def scrape_all(sources: list[SourceConfig]) -> list[ScrapeResult]:
    static_sources = [s for s in sources if s.type == "static"]
    dynamic_sources = [s for s in sources if s.type == "dynamic"]
    api_sources = [s for s in sources if s.type == "api"]

    results: list[ScrapeResult] = []
    semaphore = asyncio.Semaphore(settings.scrape_concurrency)

    async def bounded_static(client: httpx.AsyncClient, source: SourceConfig) -> ScrapeResult:
        async with semaphore:
            return await _scrape_static(client, source)

    async def bounded_api(client: httpx.AsyncClient, source: SourceConfig) -> list[ScrapeResult]:
        async with semaphore:
            return await _fetch_api(client, source)

    async with _build_client() as client:
        static_tasks = [bounded_static(client, s) for s in static_sources]
        results.extend(await asyncio.gather(*static_tasks))

        api_tasks = [bounded_api(client, s) for s in api_sources]
        for batch in await asyncio.gather(*api_tasks):
            results.extend(batch)

    if dynamic_sources:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                async def bounded_dynamic(source: SourceConfig) -> ScrapeResult:
                    async with semaphore:
                        return await _scrape_dynamic(browser, source)

                tasks = [bounded_dynamic(s) for s in dynamic_sources]
                results.extend(await asyncio.gather(*tasks))
            finally:
                await browser.close()

    return results
