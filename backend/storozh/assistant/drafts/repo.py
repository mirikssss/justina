"""Таблица assistant.drafts и проверка владельца документа."""

from uuid import UUID

from psycopg import AsyncConnection


async def document_owner(conn: AsyncConnection, document_id: UUID) -> UUID | None:
    """Владелец документа — из событий «Документов» в shared.outbox (чужие таблицы не читаем)."""
    cur = await conn.execute(
        """SELECT citizen_id FROM shared.outbox
           WHERE type IN ('document.created', 'document.changed') AND payload->'data'->>'document_id' = %s
           ORDER BY seq DESC LIMIT 1""",
        (str(document_id),),
    )
    row = await cur.fetchone()
    return row["citizen_id"] if row else None


async def save_draft(conn: AsyncConnection, *, citizen_id: UUID, document_id: UUID, draft_type: str,
                     pdf_enc: bytes) -> UUID:
    cur = await conn.execute(
        "INSERT INTO drafts (citizen_id, document_id, type, pdf_enc) VALUES (%s, %s, %s, %s) RETURNING id",
        (citizen_id, document_id, draft_type, pdf_enc),
    )
    return (await cur.fetchone())["id"]


async def get_draft(conn: AsyncConnection, draft_id: UUID, citizen_id: UUID) -> dict | None:
    cur = await conn.execute("SELECT id, type, pdf_enc FROM drafts WHERE id = %s AND citizen_id = %s",
                             (draft_id, citizen_id))
    return await cur.fetchone()
