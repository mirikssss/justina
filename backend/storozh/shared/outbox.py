"""Шина событий на таблице shared.outbox вместо брокера (Разработчик 2). Контракт тот же, что у Kafka.

Публикация идёт в той же транзакции, что и изменение данных:

    async with db.connect("documents") as conn:
        await conn.execute("INSERT INTO document_versions ...")
        await outbox.publish(conn, type="document.created", subject=uri, citizen_id=cid,
                             data={...}, dedupe_key=f"{uri}:1:created")

Потребление: у каждого потребителя свой курсор в shared.consumer_offsets. Обработчик и сдвиг курсора идут
одной транзакцией, а строка курсора берётся FOR UPDATE SKIP LOCKED, так что два экземпляра воркера
не обработают одно событие дважды. Доставка «хотя бы раз»: внешние эффекты (Telegram и т. п.)
обработчик делает идемпотентными по event.id.

    await outbox.consume("guard", {"document.created", "document.changed"}, handle)

Обработчик получает событие и соединение своей транзакции: всё, что он пишет в базу через это соединение,
коммитится вместе со сдвигом курсора.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Iterable
from typing import Any, NoReturn
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from storozh.shared import db
from storozh.shared.events import Event

log = logging.getLogger(__name__)

NOTIFY_CHANNEL = "storozh_outbox"
_WRITE_LOCK = 0x5702_0001  # сериализует запись: порядок seq = порядок коммитов, курсор ничего не пропускает

Handler = Callable[[Event, AsyncConnection], Awaitable[None]]
MAX_ATTEMPTS = 5  # T1: после стольких падений обработчика событие уходит в dead letter


async def publish(conn: AsyncConnection, *, type: str, subject: str, citizen_id: UUID, data: dict[str, Any],
                  dedupe_key: str) -> UUID:
    """Записать событие в outbox в текущей транзакции. Повтор dedupe_key возвращает id прежнего события."""
    return await publish_event(conn, Event.new(type, subject=subject, citizen_id=citizen_id, data=data,
                                               dedupe_key=dedupe_key))


async def publish_event(conn: AsyncConnection, event: Event) -> UUID:
    await conn.execute("SELECT pg_advisory_xact_lock(%s)", (_WRITE_LOCK,))
    cur = await conn.execute(
        """INSERT INTO shared.outbox (id, type, subject, citizen_id, payload, dedupe_key)
           VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (dedupe_key) DO NOTHING RETURNING seq""",
        (event.id, event.type, event.subject, event.citizen_id, Jsonb(event.to_json()), event.dedupe_key),
    )
    row = await cur.fetchone()
    if row is None:
        cur = await conn.execute("SELECT id FROM shared.outbox WHERE dedupe_key = %s", (event.dedupe_key,))
        return (await cur.fetchone())["id"]
    # NOTIFY доставляется только после COMMIT. Payload маленький: SSE и потребители сами читают outbox.
    await conn.execute("SELECT pg_notify(%s, %s)", (NOTIFY_CHANNEL, f"{row['seq']}:{event.citizen_id}"))
    return event.id


async def consume_once(consumer: db.Context, types: Iterable[str], handler: Handler,
                       name: str | None = None) -> bool:
    """Обработать одно событие. False — новых событий нет или курсор занят другим экземпляром.

    Ошибка обработчика: его записи откатываются (savepoint), попытка считается в shared.consumer_attempts.
    После MAX_ATTEMPTS событие уходит в shared.outbox_dead_letter, курсор идёт дальше (T1).
    """
    name = name or consumer
    types = sorted(types)
    failure: BaseException | None = None
    async with db.connect(consumer) as conn:
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO shared.consumer_offsets (consumer, last_seq) VALUES (%s, 0) ON CONFLICT DO NOTHING",
                (name,),
            )
        async with conn.transaction():
            cur = await conn.execute(
                "SELECT last_seq FROM shared.consumer_offsets WHERE consumer = %s FOR UPDATE SKIP LOCKED", (name,)
            )
            offset = await cur.fetchone()
            if offset is None:
                return False
            cur = await conn.execute(
                "SELECT seq, payload FROM shared.outbox WHERE seq > %s AND type = ANY(%s) ORDER BY seq LIMIT 1",
                (offset["last_seq"], types),
            )
            row = await cur.fetchone()
            if row is None:
                return False
            event = Event.model_validate(row["payload"])
            try:
                async with conn.transaction():  # savepoint: упавший обработчик откатывает только своё
                    await handler(event, conn)
            except Exception as e:
                failure = e
                if not await _count_failure(conn, name, row["seq"], event, e):
                    raise  # попытки ещё есть: откат, курсор на месте, consume() подождёт и повторит
            else:
                await conn.execute("DELETE FROM shared.consumer_attempts WHERE consumer = %s AND seq = %s",
                                   (name, row["seq"]))
            await conn.execute(
                "UPDATE shared.consumer_offsets SET last_seq = %s, updated_at = now() WHERE consumer = %s",
                (row["seq"], name),
            )
    if failure is not None:
        log.error("consumer %s: event %s (%s) moved to dead letter after %d attempts: %r",
                  name, event.id, event.type, MAX_ATTEMPTS, failure)
    return True


async def _count_failure(conn: AsyncConnection, name: str, seq: int, event: Event, error: BaseException) -> bool:
    """Записать попытку отдельной транзакцией (переживёт откат). True — попытки исчерпаны, событие в dead letter."""
    text = f"{type(error).__name__}: {error}"[:2000]
    async with db.connect("shared") as side:
        cur = await side.execute(
            """INSERT INTO shared.consumer_attempts (consumer, seq, attempts, last_error) VALUES (%s, %s, 1, %s)
               ON CONFLICT (consumer, seq) DO UPDATE
               SET attempts = shared.consumer_attempts.attempts + 1, last_error = EXCLUDED.last_error,
                   updated_at = now()
               RETURNING attempts""",
            (name, seq, text),
        )
        attempts = (await cur.fetchone())["attempts"]
    if attempts < MAX_ATTEMPTS:
        return False
    await conn.execute(
        """INSERT INTO shared.outbox_dead_letter (consumer, seq, event_id, type, citizen_id, attempts, error)
           VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (consumer, seq) DO NOTHING""",
        (name, seq, event.id, event.type, event.citizen_id, attempts, text),
    )
    await conn.execute("DELETE FROM shared.consumer_attempts WHERE consumer = %s AND seq = %s", (name, seq))
    return True


async def consume(consumer: db.Context, types: Iterable[str], handler: Handler, *, name: str | None = None,
                  idle_s: float = 0.5) -> NoReturn:
    """Бесконечный цикл потребителя. Ошибка обработчика: откат, пауза 5 с, повтор; после MAX_ATTEMPTS — dead letter."""
    log.info("consumer %s started: %s", name or consumer, sorted(types))
    while True:
        try:
            if await consume_once(consumer, types, handler, name):
                continue
        except Exception:
            log.exception("consumer %s failed, retry in 5 s", name or consumer)
            await asyncio.sleep(5)
            continue
        await asyncio.sleep(idle_s)
