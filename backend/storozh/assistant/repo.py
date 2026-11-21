"""Таблицы «Помощника»: summaries, chat_messages, drafts (схема assistant)."""

from typing import Any
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb


async def summary_exists(conn: AsyncConnection, document_id: UUID, version_no: int, lang: str) -> bool:
    cur = await conn.execute("SELECT 1 FROM summaries WHERE document_id = %s AND version_no = %s AND lang = %s",
                             (document_id, version_no, lang))
    return await cur.fetchone() is not None


async def save_summary(conn: AsyncConnection, *, citizen_id: UUID, body: dict[str, Any], model: str) -> bool:
    """False — резюме этой версии уже было (повторное событие)."""
    cur = await conn.execute(
        """INSERT INTO summaries (document_id, version_no, lang, body, citations, model, citizen_id)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (document_id, version_no, lang) DO NOTHING RETURNING id""",
        (body["document_id"], body["version_no"], body["lang"], Jsonb(body), Jsonb(body["citations"]), model,
         citizen_id),
    )
    return await cur.fetchone() is not None


async def latest_summary(conn: AsyncConnection, document_id: UUID, lang: str, citizen_id: UUID) -> dict | None:
    cur = await conn.execute(
        """SELECT body FROM summaries WHERE document_id = %s AND lang = %s AND citizen_id = %s
           ORDER BY version_no DESC LIMIT 1""",
        (document_id, lang, citizen_id),
    )
    row = await cur.fetchone()
    return row["body"] if row else None


async def document_head(conn: AsyncConnection, document_id: UUID) -> dict | None:
    """Владелец, URI и последняя версия документа — из событий «Документов» в shared.outbox (без чужих таблиц)."""
    cur = await conn.execute(
        """SELECT citizen_id, subject, (payload->'data'->>'version_no')::int AS version_no
           FROM shared.outbox
           WHERE type IN ('document.created', 'document.changed') AND payload->'data'->>'document_id' = %s
           ORDER BY seq DESC LIMIT 1""",
        (str(document_id),),
    )
    return await cur.fetchone()
