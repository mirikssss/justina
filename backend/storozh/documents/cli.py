"""Команды «Документов»: python -m storozh documents <команда>."""

import asyncio
from uuid import UUID

import typer

from storozh.shared.auth import DEV_CITIZEN_ID

app = typer.Typer(no_args_is_help=True, help="Документы: подключение OneID, демо-данные")

OAUTH_START = "https://my.gov.uz/"  # вход в кабинет перенаправляет на id.egov.uz
CABINET_URL_PREFIX = "https://my.gov.uz"
LOGIN_TIMEOUT_S = 300


@app.command()
def connect(citizen: UUID = typer.Option(DEV_CITIZEN_ID, help="citizen_id")):
    """UC-D1: видимый Chromium на id.egov.uz, человек входит сам (пароль и SMS — только там), сессия шифруется."""

    async def run() -> None:
        from playwright.async_api import async_playwright

        from storozh.documents import service
        from storozh.shared import db

        async with async_playwright() as pw:
            b = await pw.chromium.launch(headless=False)
            ctx = await b.new_context(locale="ru-RU")
            page = await ctx.new_page()
            await page.goto(OAUTH_START)
            typer.echo(f"Войдите в OneID в открывшемся окне (до {LOGIN_TIMEOUT_S // 60} мин)…")
            try:
                # TODO(Разработчик 1): уточнить по HAR признак кабинета (селектор профиля), не только URL
                await page.wait_for_url(lambda u: u.startswith(CABINET_URL_PREFIX) and "id.egov.uz" not in u,
                                        timeout=LOGIN_TIMEOUT_S * 1000)
                await page.wait_for_load_state("networkidle")
            except Exception as e:
                await b.close()
                raise typer.Exit(f"Вход не завершён: {e}. Ничего не сохранено.") from e
            state = await ctx.storage_state()
            await b.close()
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
