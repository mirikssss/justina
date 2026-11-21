"""Проверка живости кабинета my.gov.uz сессией OneID (FR-D-02, UC-D8).

Отдельно от опроса: опрос ловит истечение только тогда, когда пора читать источник, а проверка раз в 5 минут
говорит об этом заранее и останавливает опрос гражданина до нового `connect`.
"""

import asyncio

from playwright.async_api import Page

from storozh.documents.adapters import browser
from storozh.documents.adapters.mygov_car_poa import selectors as sel
from storozh.documents.ports import BrowserSession
from storozh.shared.config import settings

PROBE_TIMEOUT_S = 20


def verdict(url: str, has_cabinet_mark: bool) -> bool | None:
    """True — кабинет открыт, False — попали на вход, None — страница ещё рисуется (неопределённо)."""
    if sel.LOGIN_PATH in url:
        return False
    return True if has_cabinet_mark else None


async def _wait_verdict(page: Page) -> bool | None:
    for _ in range(PROBE_TIMEOUT_S * 2):
        v = verdict(page.url, await page.query_selector(sel.LOGGED_IN_MARK) is not None)
        if v is not None:
            return v
        await asyncio.sleep(0.5)
    return None


async def cabinet_alive(session: BrowserSession) -> bool | None:
    """True/False — определённый ответ; None — не удалось понять (сеть, медленная страница): сессию не трогаем."""
    try:
        async with browser.page(session) as page:
            await page.goto(settings.mygov_base_url.rstrip("/") + sel.LIST_PATH, wait_until="domcontentloaded")
            return await _wait_verdict(page)
    except Exception:  # noqa: BLE001 — сетевой сбой не должен считаться истечением сессии
        return None
