"""Команды «Документов»: python -m storozh documents <команда>."""

import typer

app = typer.Typer(no_args_is_help=True, help="Документы: подключение аккаунтов OneID")


@app.command()
def connect(citizen: str = typer.Option(..., help="citizen_id")):
    """Открыть видимый Chromium на id.egov.uz: человек входит сам, storage state шифруется (UC-D1)."""
    raise NotImplementedError("storozh documents connect: Разработчик 1")
