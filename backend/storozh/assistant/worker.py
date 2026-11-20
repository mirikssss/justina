"""Процесс assist-worker: резюме считается в фоне, до того как человек откроет карточку."""

from storozh.assistant.service import TOPICS, handle_event
from storozh.shared import outbox


async def run() -> None:
    await outbox.consume("assistant", TOPICS, handle_event)
