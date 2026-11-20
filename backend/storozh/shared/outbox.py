"""Шина событий на таблице shared.outbox (вместо брокера; контракт как у Kafka).

Публикация — в той же транзакции, что и изменение данных:

    async with db.connect("documents") as conn:
        await conn.execute("INSERT INTO document_versions ...")
        await outbox.publish(conn, Event.new("document.created", ...))

Потребление — у каждого контекста свой курсор в shared.consumer_offsets, обработчик и сдвиг курсора
идут одной транзакцией, поэтому побочные эффекты в базе выполняются ровно один раз.
Обработчик должен быть идемпотентным для внешних эффектов (Telegram и т. п.).

    await outbox.consume("guard", {"document.created", "document.changed"}, handle)
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Iterable

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from storozh.shared import db
from storozh.shared.events import Event

log = logging.getLogger(__name__)

NOTIFY_CHANNEL = "storozh_outbox"
_WRITE_LOCK = 0x5702_0001  # сериализует запись: порядок seq = порядок коммитов, курсор ничего не пропускает

Handler = Callable[[Event, AsyncConnection], Awaitable[None]]


async def publish(conn: AsyncConnection, event: Event) -> bool:
    """Записать событие в outbox в текущей транзакции. False — такой dedupe_key уже был."""
    await conn.execute("SELECT pg_advisory_xact_lock(%s)", (_WRITE_LOCK,))
    cur = await conn.execute(
        """INSERT INTO shared.outbox (event_id, topic, citizen_id, payload, dedupe_key)
           VALUES (%s, %s, %s, %s, %s) ON CONFLICT (dedupe_key) DO NOTHING RETURNING seq""",
        (event.id, event.type, event.citizen_id, Jsonb(event.to_json()), event.dedupe_key),
    )
    row = await cur.fetchone()
    if row is None:
        return False
    # NOTIFY доставляется только после COMMIT; payload маленький: SSE и потребители сами читают outbox
    await conn.execute("SELECT pg_notify(%s, %s)", (NOTIFY_CHANNEL, f"{row['seq']}:{event.citizen_id}"))
    return True


async def _next_batch(conn: AsyncConnection, consumer: str, topics: list[str], limit: int) -> list[dict]:
    await conn.execute(
        "INSERT INTO shared.consumer_offsets (consumer, last_seq) VALUES (%s, 0) ON CONFLICT DO NOTHING",
        (consumer,),
    )
    cur = await conn.execute(
        """SELECT o.seq, o.payload FROM shared.outbox o, shared.consumer_offsets c
           WHERE c.consumer = %s AND o.seq > c.last_seq AND o.topic = ANY(%s)
           ORDER BY o.seq LIMIT %s""",
        (consumer, topics, limit),
    )
    return await cur.fetchall()


async def consume_once(context: db.Context, topics: Iterable[str], handler: Handler,
                       consumer: str | None = None, limit: int = 50) -> int:
    """Обработать накопившиеся события. Возвращает, сколько обработано."""
    consumer = consumer or context
    topics = sorted(topics)
    done = 0
    async with db.connect(context) as conn:
        rows = await _next_batch(conn, consumer, topics, limit)
    for row in rows:
        async with db.connect(context) as conn:
            async with conn.transaction():
                await handler(Event.model_validate(row["payload"]), conn)
                await conn.execute(
                    "UPDATE shared.consumer_offsets SET last_seq = %s, updated_at = now() WHERE consumer = %s",
                    (row["seq"], consumer),
                )
        done += 1
    return done


async def consume(context: db.Context, topics: Iterable[str], handler: Handler,
                  consumer: str | None = None, idle_s: float = 1.0) -> None:
    """Бесконечный цикл потребителя: читает пачками, между пачками ждёт NOTIFY или idle_s."""
    log.info("consumer %s started: %s", consumer or context, sorted(topics))
    while True:
        try:
            n = await consume_once(context, topics, handler, consumer)
        except Exception:
            log.exception("consumer %s failed, retry in 5 s", consumer or context)
            await asyncio.sleep(5)
            continue
        if n == 0:
            await asyncio.sleep(idle_s)
