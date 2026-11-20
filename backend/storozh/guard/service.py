"""Сценарии «Сторожа»: событие -> тревога -> подтверждённое действие -> проверка по источнику."""

from psycopg import AsyncConnection

from storozh.shared.events import Event

TOPICS = {"document.created", "document.changed", "document.status_changed", "document.disappeared",
          "source.session_expired"}


async def handle_event(event: Event, conn: AsyncConnection) -> None:
    """Правила -> guard.alerts (event_id unique) -> alert.created. Объяснение от assistant с таймаутом 5 с."""
    raise NotImplementedError("guard.handle_event: Разработчик 3")
