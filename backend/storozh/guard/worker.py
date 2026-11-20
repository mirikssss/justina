"""Процесс guard-worker: потребитель событий document.* со своим курсором."""

from storozh.guard.service import TOPICS, handle_event
from storozh.shared import outbox


async def run() -> None:
    await outbox.consume("guard", TOPICS, handle_event)
