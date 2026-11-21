"""Playwright для адаптеров.

my.gov.uz привязывает сессию к ключу устройства (`gateway-attest` в IndexedDB, неэкспортируемый CryptoKey) и подписывает
им запросы. В JSON-снимок (storage state) такой ключ не попадает, поэтому перенесённая сессия получает 403.
Поэтому у гражданина есть ПОСТОЯННЫЙ профиль Chromium (settings.browser_profiles_dir/<citizen_id>): `connect` входит в нём,
сборщик открывает тот же профиль. Профиль хранит сессию на диске без шифрования приложения: каталог 0700, не в git;
в целевом состоянии доступ к данным идёт через интеграцию MyGov, а не через сессию человека.
Без профиля (макет, тесты) работает прежний путь: общий Chromium и storage state.
"""

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

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


def profile_dir(citizen_id) -> Path:
    return settings.browser_profiles_dir / str(citizen_id)


def _load_cookies(profile: Path) -> list | None:
    f = profile / "session_cookies.json"
    return json.loads(f.read_text()) if f.exists() else None


def _save_cookies(profile: Path, cookies: list) -> None:
    f = profile / "session_cookies.json"
    f.write_text(json.dumps(cookies))
    f.chmod(0o600)


_shared: dict = {}  # citizen_id -> открытый persistent-контекст: живёт, пока жив процесс (команда `documents live`)


def set_shared_context(citizen_id, ctx) -> None:
    """Долгоживущий вход: токены портала лежат в сессионных куках и меняются, повторить их из файла нельзя."""
    _shared[citizen_id] = ctx


@asynccontextmanager
async def page(session: BrowserSession) -> AsyncIterator[Page]:
    shared = _shared.get(session.citizen_id)
    if shared is not None:
        pg = await shared.new_page()
        try:
            yield pg
        finally:
            await pg.close()
        return
    profile = profile_dir(session.citizen_id)
    if profile.exists():  # постоянный профиль: единственный способ сохранить ключ устройства портала
        await browser()  # поднимает playwright
        ctx = await _pw.chromium.launch_persistent_context(
            str(profile), headless=settings.collector_headless, locale="ru-RU")
        # Сессионные куки (без срока жизни) профиль теряет при закрытии: возвращаем их из сохранённого состояния.
        cookies = _load_cookies(profile) or session.storage_state.get("cookies")
        if cookies:
            await ctx.add_cookies(cookies)
    else:
        ctx = await (await browser()).new_context(storage_state=session.storage_state, locale="ru-RU")
    try:
        yield await ctx.new_page()
    finally:
        if profile.exists():  # портал обновляет токен в куках: следующий заход должен получить свежие, а не исходные
            _save_cookies(profile, await ctx.cookies())
        await ctx.close()


async def close() -> None:
    global _browser, _pw
    if _browser is not None:
        await _browser.close()
        await _pw.stop()
        _browser = _pw = None
