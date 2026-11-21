"""T5: один LISTEN на процесс api вместо соединения на каждую вкладку /stream.

Хаб держит одно соединение с LISTEN storozh_outbox и будит подписчиков нужного гражданина (asyncio.Event).
Payload уведомления — только "seq:citizen_id"; сами события подписчик читает из outbox через общий пул.
Соединение упало — переподключаемся с паузой и будим всех: они догонят пропущенное по last_seq.
"""

import asyncio
import contextlib
import logging
from collections import defaultdict
from uuid import UUID

import psycopg

from storozh.shared import outbox
from storozh.shared.config import settings

log = logging.getLogger(__name__)


class StreamHub:
    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Event]] = defaultdict(set)
        self._task: asyncio.Task | None = None
        self.connected = asyncio.Event()

    def subscribe(self, citizen_id: UUID) -> asyncio.Event:
        ev = asyncio.Event()
        self._subs[str(citizen_id)].add(ev)
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name="stream-hub")
        return ev

    def unsubscribe(self, citizen_id: UUID, ev: asyncio.Event) -> None:
        subs = self._subs.get(str(citizen_id))
        if subs is not None:
            subs.discard(ev)
            if not subs:
                del self._subs[str(citizen_id)]

    @property
    def subscribers(self) -> int:
        return sum(len(s) for s in self._subs.values())

    def _wake(self, citizen_id: str | None = None) -> None:
        targets = self._subs.get(citizen_id, ()) if citizen_id else [e for s in self._subs.values() for e in s]
        for ev in list(targets):
            ev.set()

    async def _run(self) -> None:
        delay = 1.0
        while self._subs:
            try:
                async with await psycopg.AsyncConnection.connect(settings.database_url, autocommit=True) as conn:
                    await conn.execute("SET ROLE storozh_platform")
                    await conn.execute(f"LISTEN {outbox.NOTIFY_CHANNEL}")
                    self.connected.set()
                    self._wake()  # после (пере)подключения все догоняют пропущенное
                    delay = 1.0
                    while self._subs:
                        async for n in conn.notifies(timeout=5.0):
                            self._wake(n.payload.rsplit(":", 1)[-1])
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("stream hub: LISTEN connection lost, retry in %.0f s", delay)
                self.connected.clear()
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30.0)
        self.connected.clear()

    async def close(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._task
            self._task = None


hub = StreamHub()
