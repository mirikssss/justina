"""Общее для адаптеров кабинета my.gov.uz: открыть страницу сессией OneID и отдать HTML после отрисовки."""

from playwright.async_api import TimeoutError as PlaywrightTimeout

from storozh.documents.adapters import browser
from storozh.documents.adapters.mygov_car_poa import selectors as sel
from storozh.documents.ports import BrowserSession
from storozh.shared.config import settings


async def cabinet_html(session: BrowserSession, path: str, content_selector: str, source_id: str,
                       content_timeout_ms: int = 15_000) -> str:
    """Открыть страницу сессией OneID и вернуть HTML после отрисовки.

    Сначала подтверждаем, что мы в кабинете (иначе SessionExpired), потом ждём содержимое: страница рисует списки
    после расшифровки ответа API, уже после блока профиля. Содержимого нет за таймаут — список считаем пустым.
    """
    async with browser.page(session) as page:
        await page.goto(settings.mygov_base_url.rstrip("/") + path, wait_until="domcontentloaded")
        try:
            await page.wait_for_selector(sel.LOGGED_IN_MARK, timeout=20_000)
        except PlaywrightTimeout:
            raise browser.SessionExpired(source_id) from None
        if sel.LOGIN_PATH in page.url:
            raise browser.SessionExpired(source_id)
        try:
            await page.wait_for_selector(content_selector, timeout=content_timeout_ms)
        except PlaywrightTimeout:
            pass  # пустой список: на странице нет карточек
        await browser.settle(page)
        return await page.content()
