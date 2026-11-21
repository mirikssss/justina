"""Команды «Документов»: python -m storozh documents <команда>."""

import asyncio
from uuid import UUID

import typer

from storozh.shared.auth import DEV_CITIZEN_ID

app = typer.Typer(no_args_is_help=True, help="Документы: подключение OneID, демо-данные")

OAUTH_START = "https://my.gov.uz/"  # вход в кабинет перенаправляет на id.egov.uz
CABINET_URL_PREFIX = "https://my.gov.uz"
LOGIN_TIMEOUT_S = 600


@app.command()
def connect(citizen: UUID = typer.Option(DEV_CITIZEN_ID, help="citizen_id")):
    """UC-D1: видимый Chromium на id.egov.uz, человек входит сам (пароль и SMS — только там), сессия шифруется."""

    async def run() -> None:
        from playwright.async_api import async_playwright

        from storozh.documents import service
        from storozh.documents.adapters import browser
        from storozh.documents.adapters.mygov_car_poa import selectors as mygov_sel
        from storozh.documents.adapters.soliq_legal import selectors as soliq_sel
        from storozh.shared import db
        from storozh.shared.config import settings

        async def wait_ok(page, what: str, check, timeout_s: int) -> bool:
            """Ждём настоящий признак входа (а не просто адрес): человек может долго вводить SMS."""
            try:
                await check(page, timeout_s * 1000)
                return True
            except Exception as e:  # noqa: BLE001
                typer.echo(f"{what}: вход не подтверждён ({type(e).__name__}).")
                return False

        async def mygov_ok(page, ms):
            await page.wait_for_selector(mygov_sel.LOGGED_IN_MARK, timeout=ms)

        async def birdarcha_ok(page, ms):
            await page.wait_for_function(
                """() => { try { const a = JSON.parse(JSON.parse(localStorage.getItem('persist:auth')).tokens);
                                 return !!a.accessToken && a.accessToken.length > 20; } catch (e) { return false; } }""",
                timeout=ms)

        async def soliq_ok(page, ms):
            await page.wait_for_selector(soliq_sel.COMPANY_READY, timeout=ms)

        async with async_playwright() as pw:
            profile = browser.profile_dir(citizen)
            profile.mkdir(parents=True, exist_ok=True)
            profile.chmod(0o700)
            ctx = await pw.chromium.launch_persistent_context(str(profile), headless=False, locale="ru-RU")
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            await page.goto(settings.mygov_base_url.rstrip("/") + mygov_sel.LIST_PATH)  # без входа перекинет на OneID
            typer.echo(f"Войдите в OneID в открывшемся окне (до {LOGIN_TIMEOUT_S // 60} мин)…")
            if not await wait_ok(page, "my.gov.uz", mygov_ok, LOGIN_TIMEOUT_S):
                await ctx.close()
                raise typer.Exit("Вход в my.gov.uz не завершён. Ничего не сохранено.")
            await page.wait_for_load_state("networkidle")
            typer.echo("my.gov.uz: вошли. Подключаю Birdarcha…")
            await page.goto(settings.birdarcha_base_url.rstrip("/") + "/dashboard")
            typer.echo("Если Birdarcha просит войти — нажмите вход через OneID в окне (до 2 мин).")
            if await wait_ok(page, "Birdarcha", birdarcha_ok, 120):
                typer.echo("Birdarcha: вошли. Подключаю my.soliq.uz…")
            await page.goto(settings.soliq_base_url.rstrip("/") + soliq_sel.BASE_PATH + soliq_sel.COMPANY_PAGE)
            typer.echo("Если my.soliq.uz просит войти или выбрать кабинет юрлица — сделайте это в окне (до 3 мин).")
            if await wait_ok(page, "my.soliq.uz", soliq_ok, 180):
                typer.echo("my.soliq.uz: вошли.")
            await page.goto(settings.mygov_base_url.rstrip("/") + mygov_sel.LIST_PATH)  # токен my.gov.uz — в localStorage этого origin
            await page.wait_for_load_state("networkidle")
            state = await ctx.storage_state()
            browser._save_cookies(profile, state["cookies"])
            await ctx.close()
        await service.save_session(citizen, dict(state))
        await db.close_all()
        typer.echo(f"Сессия сохранена для {citizen}, источники включены.")

    asyncio.run(run())


@app.command()
def seed(citizen: UUID = typer.Option(DEV_CITIZEN_ID, help="citizen_id"),
         step: str = typer.Option("base", help="base | new_poa | revoke")):
    """Демо-данные через настоящий ingest: лента, версии и события document.* без живого кабинета."""

    async def run() -> None:
        from storozh.documents import demo, service
        from storozh.shared import db

        for snap in demo.snapshots(citizen, step):
            typer.echo(f"{snap.source}: {await service.ingest_snapshot(snap)}")
        await db.close_all()

    asyncio.run(run())


@app.command()
def mockportal(port: int = typer.Option(8765, help="порт макета my.gov.uz")):
    """Тестовый макет my.gov.uz (вымышленные данные): страницы «Мои заявки» для прогона настоящего адаптера."""
    import uvicorn

    typer.echo(f"Макет на http://localhost:{port}/_mock ; сборщику: MYGOV_BASE_URL=http://localhost:{port}")
    uvicorn.run("storozh.documents.mockportal.app:app", port=port, log_level="warning")


@app.command("poll-once")
def poll_once(citizen: UUID = typer.Option(DEV_CITIZEN_ID, help="citizen_id"),
              source: str = typer.Option("mygov.car_poa", help="source_id адаптера")):
    """Один опрос адаптера пустой сессией (для макета и отладки, без OneID) через настоящий подписанный ingest."""

    async def run() -> None:
        import httpx

        from storozh.documents.adapters import ADAPTERS, browser
        from storozh.documents.ports import BrowserSession
        from storozh.documents.worker import poll_with_session
        from storozh.shared.config import settings

        adapter = next((a for a in ADAPTERS if a.source_id == source), None)
        if adapter is None:
            raise typer.Exit(f"Неизвестный источник {source}")
        session = BrowserSession(citizen_id=citizen, storage_state={"cookies": [], "origins": []})
        try:
            async with httpx.AsyncClient(base_url=settings.api_internal_url, timeout=30) as client:
                typer.echo(await poll_with_session(session, adapter, client))
        finally:
            await browser.close()

    asyncio.run(run())


@app.command()
def live(citizen: UUID = typer.Option(DEV_CITIZEN_ID, help="citizen_id")):
    """Живой режим: один видимый Chromium с профилем гражданина входит один раз и остаётся открытым, сборщик работает в нём.

    Окно не закрывайте: токены my.gov.uz живут в сессионных куках и меняются, поэтому их нельзя перенести между запусками.
    """

    async def run() -> None:
        from playwright.async_api import async_playwright

        from storozh.documents import service, worker
        from storozh.documents.adapters import browser
        from storozh.documents.adapters.mygov_car_poa import selectors as mygov_sel
        from storozh.documents.adapters.soliq_legal import selectors as soliq_sel
        from storozh.shared import db
        from storozh.shared.config import settings

        async def ensure(page, url: str, ok_js_or_selector: str, what: str, hint: str, wait_s: int) -> None:
            await page.goto(url, wait_until="domcontentloaded", timeout=90_000)
            try:
                if ok_js_or_selector.startswith("() =>"):
                    await page.wait_for_function(ok_js_or_selector, timeout=15_000)
                else:
                    await page.wait_for_selector(ok_js_or_selector, timeout=15_000)
                typer.echo(f"{what}: вход есть.")
                return
            except Exception:  # noqa: BLE001
                typer.echo(f"{what}: нужен вход. {hint} (жду до {wait_s // 60} мин)")
            if ok_js_or_selector.startswith("() =>"):
                await page.wait_for_function(ok_js_or_selector, timeout=wait_s * 1000)
            else:
                await page.wait_for_selector(ok_js_or_selector, timeout=wait_s * 1000)
            typer.echo(f"{what}: вошли.")

        birdarcha_js = ("() => { try { const a = JSON.parse(JSON.parse(localStorage.getItem('persist:auth')).tokens);"
                        " return !!a.accessToken && a.accessToken.length > 20; } catch (e) { return false; } }")
        async with async_playwright() as pw:
            profile = browser.profile_dir(citizen)
            profile.mkdir(parents=True, exist_ok=True)
            profile.chmod(0o700)
            ctx = await pw.chromium.launch_persistent_context(str(profile), headless=False, locale="ru-RU")
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            await ensure(page, settings.mygov_base_url.rstrip("/") + mygov_sel.LIST_PATH, mygov_sel.LOGGED_IN_MARK,
                         "my.gov.uz", "Войдите через OneID в окне", LOGIN_TIMEOUT_S)
            await ensure(page, settings.birdarcha_base_url.rstrip("/") + "/dashboard", birdarcha_js,
                         "Birdarcha", "Нажмите вход через OneID", 180)
            await ensure(page, settings.soliq_base_url.rstrip("/") + soliq_sel.BASE_PATH + soliq_sel.COMPANY_PAGE,
                         soliq_sel.COMPANY_READY, "my.soliq.uz", "Войдите и выберите кабинет юрлица", 240)
            await page.goto("about:blank")
            browser.set_shared_context(citizen, ctx)
            await service.save_session(citizen, dict(await ctx.storage_state()))
            typer.echo("Всё подключено. Сборщик работает; окно браузера не закрывайте. Ctrl+C — остановить.")
            try:
                await worker.run()
            finally:
                await db.close_all()
                await ctx.close()

    asyncio.run(run())
