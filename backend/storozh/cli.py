"""Единая точка входа: python -m storozh <команда>. Один образ — разные процессы в docker compose."""

import asyncio
import logging

import typer

from storozh.assistant.rag.cli import app as rag_app
from storozh.shared import logs

app = typer.Typer(no_args_is_help=True)
app.add_typer(rag_app, name="rag")

@app.callback()
def _setup() -> None:
    logs.setup(logging.INFO)

@app.command()
def api(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """HTTP API (все роутеры)."""
    import uvicorn

    uvicorn.run("storozh.main:app", host=host, port=port, reload=reload)

@app.command()
def worker(name: str = typer.Argument(..., help="collector | guard | bot | assistant")):
    """Фоновый процесс контекста."""
    if name == "collector":
        from storozh.documents.worker import run
    elif name == "guard":
        from storozh.guard.worker import run
    elif name == "bot":
        from storozh.guard.bot.main import run
    elif name == "assistant":
        from storozh.assistant.worker import run
    else:
        raise typer.BadParameter(f"unknown worker {name!r}")
    asyncio.run(run())

@app.command()
def migrate():
    """Применить SQL-миграции всех контекстов (storozh/migrations/<context>/)."""
    from storozh.shared import migrate as m

    applied = m.run()
    print("\n".join(applied) if applied else "nothing to apply")

@app.command()
def connect(citizen: str = typer.Option(..., help="citizen_id")):
    """Открыть видимый Chromium на id.egov.uz: человек входит сам, сессия шифруется (Разработчик 1)."""
    raise NotImplementedError("storozh connect: Разработчик 1")
