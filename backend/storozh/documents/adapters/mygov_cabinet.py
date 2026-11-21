"""Общее для адаптеров кабинета my.gov.uz: открыть страницу сессией OneID и отдать HTML после отрисовки."""

from playwright.async_api import TimeoutError as PlaywrightTimeout

from storozh.documents.adapters import browser
from storozh.documents.adapters.mygov_car_poa import selectors as sel
from storozh.documents.ports import BrowserSession
from storozh.shared.config import settings


async def cabinet_html(session: BrowserSession, path: str, ready_selector: str, source_id: str) -> str:
    """Страница рисуется после расшифровки ответа API, поэтому ждём ready_selector. Вход вместо кабинета — SessionExpired."""
    async with browser.page(session) as page:
        await page.goto(settings.mygov_base_url.rstrip("/") + path, wait_until="domcontentloaded")
        try:
            await page.wait_for_selector(f"{sel.LOGGED_IN_MARK}, {ready_selector}", timeout=15_000)
        except PlaywrightTimeout:
            raise browser.SessionExpired(source_id) from None
        if sel.LOGIN_PATH in page.url or not await page.query_selector(sel.LOGGED_IN_MARK):
            raise browser.SessionExpired(source_id)
        await page.wait_for_load_state("networkidle")
        return await page.content()
