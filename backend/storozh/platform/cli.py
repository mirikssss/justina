"""storozh platform … — служебные команды «Платформы» для разработки и демо."""

import asyncio
from uuid import UUID

import typer

from storozh.shared.auth import DEV_CITIZEN_ID

app = typer.Typer(no_args_is_help=True)


@app.command("seed-citizen")
def seed_citizen(citizen: UUID = typer.Option(DEV_CITIZEN_ID), name: str = "Азиз А.",
                 pinfl: str = typer.Option("30101900000000", help="ПИНФЛ (шифруется)"), lang: str = "ru"):
    """Создать или обновить гражданина (для /me и PDF-заявлений)."""

    async def run() -> None:
        from storozh.platform import service
        from storozh.shared import db

        await service.seed_citizen(citizen, name, pinfl, lang)
        await db.close_all()

    asyncio.run(run())
    typer.echo(f"citizen {citizen} ok")


@app.command("login-link")
def login_link(citizen: UUID = typer.Option(DEV_CITIZEN_ID)):
    """Одноразовая ссылка входа без бота (для демо и отладки)."""

    async def run() -> str:
        from storozh.platform import service
        from storozh.shared import db

        try:
            return await service.issue_login_link(None, citizen)
        finally:
            await db.close_all()

    typer.echo(asyncio.run(run()))
