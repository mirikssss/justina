"""Playwright для адаптеров: один Chromium на процесс, контекст на сессию OneID."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from playwright.async_api import Browser, Page, async_playwright

from storozh.documents.ports import BrowserSession
from storozh.shared.config import settings

_browser: Browser | None = None
_pw = None


class SessionExpired(Exception):
    """Кабинет не открылся: сессия OneID истекла (UC-D8)."""


async def browser() -> Browser:
    global _browser, _pw
    if _browser is None:
        _pw = await async_playwright().start()
        _browser = await _pw.chromium.launch(headless=settings.collector_headless)
    return _browser


@asynccontextmanager
async def page(session: BrowserSession) -> AsyncIterator[Page]:
    ctx = await (await browser()).new_context(storage_state=session.storage_state, locale="ru-RU")
    try:
        yield await ctx.new_page()
    finally:
        await ctx.close()


async def close() -> None:
    global _browser, _pw
    if _browser is not None:
        await _browser.close()
        await _pw.stop()
        _browser = _pw = None
