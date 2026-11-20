"""Сценарии «Помощника»: фоновое резюме по событиям документов."""

from psycopg import AsyncConnection

from storozh.shared.events import Event

TOPICS = {"document.created", "document.changed"}


async def handle_event(event: Event, conn: AsyncConnection) -> None:
    """Резюме новой версии -> assistant.summaries (кэш на версию и язык) -> summary.ready."""
    raise NotImplementedError("assistant.handle_event: Разработчик 3")
