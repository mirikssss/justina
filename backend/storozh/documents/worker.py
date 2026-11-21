"""Процесс collector: опрос источников и отправка SourceSnapshot в Ingestion API.

Сборщик не пишет в базу документов напрямую: только POST /internal/ingest/snapshots с подписью HMAC.
В целевом состоянии тот же контракт шлёт шина межведомственной интеграции MyGov.

Вежливый опрос (NFR-D-03, NFR-D-04): интервал адаптера ±3 с, одна сессия на аккаунт (SessionProvider),
при ошибке пауза 20 → 40 → 80 с … до 10 мин; ошибка одного адаптера не останавливает остальные.
Внеочередной опрос — NOTIFY storozh_refresh (кнопка «Обновить» и request_refresh «Сторожа»).
"""

import asyncio
import json
import logging
import random
import time
import uuid
from datetime import UTC, datetime
from uuid import UUID

import httpx

from storozh.documents import service
from storozh.documents.adapters import ADAPTERS, browser, liveness
from storozh.documents.ports import BrowserSession, SourceAdapter
from storozh.shared import crypto, db
from storozh.shared import logging as logs
from storozh.shared.config import settings
from storozh.shared.contracts import SourceSnapshot

log = logging.getLogger(__name__)

JITTER_S = 3
BACKOFF_START_S, BACKOFF_MAX_S = 20, 600
SESSION_CHECK_S = 300
DISCOVER_S = 30


def next_delay(interval_s: int, failures: int) -> float:
    """Пауза до следующего опроса: интервал ±3 с; при ошибках — 20, 40, 80 … 600 с."""
    if failures:
        return min(BACKOFF_START_S * 2 ** (failures - 1), BACKOFF_MAX_S)
    return max(1.0, interval_s + random.uniform(-JITTER_S, JITTER_S))


async def send_snapshot(snapshot: SourceSnapshot, client: httpx.AsyncClient) -> dict:
    body = snapshot.model_dump_json().encode()
    ts = int(time.time())
    r = await client.post("/internal/ingest/snapshots", content=body, headers={
        "Content-Type": "application/json", "X-Timestamp": str(ts), "X-Signature": crypto.sign_internal(body, ts),
    })
    r.raise_for_status()
    return r.json()


async def poll_once(citizen_id: UUID, adapter: SourceAdapter, client: httpx.AsyncClient) -> dict:
    async with service.session_provider().get(citizen_id) as session:
        return await poll_with_session(session, adapter, client)


async def poll_with_session(session: BrowserSession, adapter: SourceAdapter, client: httpx.AsyncClient) -> dict:
    """Один опрос уже выданной сессией: fetch -> normalize -> подписанный снимок в Ingestion API."""
    citizen_id = session.citizen_id
    raws = await adapter.fetch(session)
    docs = [adapter.normalize(r) for r in raws]
    snapshot = SourceSnapshot(snapshot_id=uuid.uuid4(), citizen_id=citizen_id, source=adapter.source_id,
                              fetched_at=datetime.now(UTC), complete=adapter.complete, documents=docs)
    return await send_snapshot(snapshot, client)


class Collector:
    def __init__(self) -> None:
        self.wakeups: dict[tuple[UUID, str], asyncio.Event] = {}
        self.tasks: dict[tuple[UUID, str], asyncio.Task] = {}
        self.client = httpx.AsyncClient(base_url=settings.api_internal_url, timeout=30)

    async def source_loop(self, citizen_id: UUID, adapter: SourceAdapter) -> None:
        key = (citizen_id, adapter.source_id)
        wake = self.wakeups.setdefault(key, asyncio.Event())
        failures = 0
        while True:
            rid_token = logs.request_id.set(uuid.uuid4().hex)
            try:
                result = await poll_once(citizen_id, adapter, self.client)
                failures = 0
                log.info("poll ok", extra={"source": adapter.source_id, "citizen_id": str(citizen_id), **result})
            except browser.SessionExpired:
                log.warning("session expired for %s", citizen_id)
                await service.expire_session(citizen_id)
                return
            except NotImplementedError as e:
                log.warning("%s not ready: %s", adapter.source_id, e)
                return
            except Exception as e:
                failures += 1
                log.exception("%s %s failed (%s in a row)", adapter.source_id, citizen_id, failures)
                await service.record_poll_error(citizen_id, adapter.source_id, f"{type(e).__name__}: {e}")
            finally:
                logs.request_id.reset(rid_token)
            wake.clear()
            try:
                await asyncio.wait_for(wake.wait(), timeout=next_delay(adapter.poll_interval_s, failures))
            except TimeoutError:
                pass

    def ensure(self, citizens: list[UUID]) -> None:
        active = set(citizens)
        for key, task in list(self.tasks.items()):
            if key[0] not in active or task.done():
                task.cancel()
                del self.tasks[key]
        for citizen_id in active:
            for adapter in ADAPTERS:
                key = (citizen_id, adapter.source_id)
                if key not in self.tasks:
                    self.tasks[key] = asyncio.create_task(self.source_loop(citizen_id, adapter))

    async def check_sessions(self) -> None:
        """FR-D-02: раз в 5 минут открыть кабинет каждой активной сессией; вход вместо кабинета — session_expired."""
        for citizen_id in await service.active_citizens():
            rid_token = logs.request_id.set(uuid.uuid4().hex)
            try:
                async with service.session_provider().get(citizen_id) as session:  # под advisory lock, как опрос
                    alive = await liveness.cabinet_alive(session)
                if alive is False:
                    log.warning("session expired", extra={"citizen_id": str(citizen_id), "check": "liveness"})
                    await service.expire_session(citizen_id)
                elif alive is None:
                    log.info("liveness inconclusive", extra={"citizen_id": str(citizen_id)})
            except Exception:
                log.exception("liveness check failed", extra={"citizen_id": str(citizen_id)})
            finally:
                logs.request_id.reset(rid_token)

    async def listen_refresh(self) -> None:
        """NOTIFY storozh_refresh {"citizen_id", "source"} -> разбудить цикл источника."""
        p = await db.pool("documents")
        async with p.connection() as conn:
            await conn.set_autocommit(True)
            await conn.execute(f"LISTEN {service.REFRESH_CHANNEL}")
            async for note in conn.notifies():
                msg = json.loads(note.payload)
                key = (UUID(msg["citizen_id"]), msg["source"])
                if key in self.wakeups:
                    self.wakeups[key].set()

    async def run(self) -> None:
        asyncio.create_task(self.listen_refresh())
        last_check = 0.0
        while True:
            self.ensure(await service.active_citizens())
            if time.monotonic() - last_check > SESSION_CHECK_S:
                last_check = time.monotonic()
                asyncio.create_task(self.check_sessions())
            await asyncio.sleep(DISCOVER_S)


async def run() -> None:
    log.info("collector: adapters %s", [a.source_id for a in ADAPTERS])
    try:
        await Collector().run()
    finally:
        await browser.close()
