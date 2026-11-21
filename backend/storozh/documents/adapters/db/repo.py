"""SQL «Документов». Соединение — shared.db.connect("documents"): search_path = documents, shared."""

from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb


async def claim_snapshot(conn: AsyncConnection, *, snapshot_id: UUID, citizen_id: UUID, source: str,
                         complete: bool, documents_count: int, fetched_at: datetime) -> bool:
    """True — снимок новый. False — уже принимали (идемпотентность по snapshot_id)."""
    cur = await conn.execute(
        """INSERT INTO snapshots (snapshot_id, citizen_id, source, complete, documents_count, fetched_at)
           VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING RETURNING snapshot_id""",
        (snapshot_id, citizen_id, source, complete, documents_count, fetched_at),
    )
    return await cur.fetchone() is not None


async def lock_document(conn: AsyncConnection, citizen_id: UUID, uri: str) -> dict | None:
    """Строка документа с хешем и payload текущей версии; FOR UPDATE — параллельный снимок подождёт."""
    cur = await conn.execute(
        """SELECT d.id, d.current_version, d.status, v.content_hash, v.payload
           FROM documents d JOIN document_versions v ON v.document_id = d.id AND v.version_no = d.current_version
           WHERE d.citizen_id = %s AND d.uri = %s FOR UPDATE OF d""",
        (citizen_id, uri),
    )
    return await cur.fetchone()


async def insert_document(conn: AsyncConnection, *, citizen_id: UUID, doc: dict[str, Any], seen_at: datetime) -> UUID:
    cur = await conn.execute(
        """INSERT INTO documents (uri, citizen_id, kind, source, status, owner_role, title, current_version,
                                  updated_at, first_seen_at, last_seen_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, 1, %s, %s, %s) RETURNING id""",
        (doc["uri"], citizen_id, doc["kind"], doc["source"], doc["status"], doc["owner_role"], doc["title"],
         seen_at, seen_at, seen_at),
    )
    return (await cur.fetchone())["id"]


async def insert_version(conn: AsyncConnection, *, document_id: UUID, version_no: int, content_hash: str,
                         payload: dict[str, Any], snapshot_id: UUID, fetched_at: datetime,
                         raw_enc: bytes | None = None) -> None:
    await conn.execute(
        """INSERT INTO document_versions (document_id, version_no, content_hash, payload, raw_enc, snapshot_id,
                                          fetched_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (document_id, version_no, content_hash, Jsonb(payload), raw_enc, snapshot_id, fetched_at),
    )


async def bump_document(conn: AsyncConnection, *, document_id: UUID, version_no: int, doc: dict[str, Any],
                        seen_at: datetime) -> None:
    await conn.execute(
        """UPDATE documents SET current_version = %s, status = %s, owner_role = %s, title = %s, kind = %s,
                  updated_at = %s, last_seen_at = %s, missing_count = 0
           WHERE id = %s""",
        (version_no, doc["status"], doc["owner_role"], doc["title"], doc["kind"], seen_at, seen_at, document_id),
    )


async def touch_document(conn: AsyncConnection, document_id: UUID, seen_at: datetime) -> None:
    await conn.execute("UPDATE documents SET last_seen_at = %s, missing_count = 0 WHERE id = %s",
                       (seen_at, document_id))


async def mark_missing(conn: AsyncConnection, *, citizen_id: UUID, source: str, present_uris: list[str]) -> list[dict]:
    """+1 к missing_count у документов источника, которых нет в полном снимке. Возвращает их новые значения."""
    cur = await conn.execute(
        """UPDATE documents SET missing_count = missing_count + 1
           WHERE citizen_id = %s AND source = %s AND NOT (uri = ANY(%s))
           RETURNING id, uri, current_version, missing_count""",
        (citizen_id, source, present_uris),
    )
    return await cur.fetchall()


async def source_poll_result(conn: AsyncConnection, *, citizen_id: UUID, source: str, ok: bool,
                             error: str | None = None) -> None:
    await conn.execute(
        """INSERT INTO sources (source_id, citizen_id, last_poll_at, last_ok_at, last_error)
           VALUES (%s, %s, now(), CASE WHEN %s THEN now() END, %s)
           ON CONFLICT (citizen_id, source_id) DO UPDATE SET
               last_poll_at = now(),
               last_ok_at = CASE WHEN %s THEN now() ELSE sources.last_ok_at END,
               last_error = %s""",
        (source, citizen_id, ok, error, ok, error),
    )


# --- чтение для API ---

async def list_documents(conn: AsyncConnection, *, citizen_id: UUID, kind: str | None, status: str | None,
                         q: str | None, after: tuple[datetime, UUID] | None, limit: int) -> list[dict]:
    where, args = ["d.citizen_id = %s"], [citizen_id]
    if kind:
        where.append("d.kind = %s")
        args.append(kind)
    if status:
        where.append("d.status = %s")
        args.append(status)
    if q:
        where.append("(d.title ILIKE %s OR d.uri ILIKE %s)")
        args += [f"%{q}%", f"%{q}%"]
    if after:
        where.append("(d.updated_at, d.id) < (%s, %s)")
        args += [after[0], after[1]]
    cur = await conn.execute(
        f"""SELECT d.id, d.uri, d.kind, d.title, d.status, d.owner_role, d.source, d.current_version,
                   d.first_seen_at, d.updated_at, v.payload
            FROM documents d JOIN document_versions v ON v.document_id = d.id AND v.version_no = d.current_version
            WHERE {' AND '.join(where)}
            ORDER BY d.updated_at DESC, d.id DESC LIMIT %s""",  # в where только плейсхолдеры
        (*args, limit),
    )
    return await cur.fetchall()


async def get_document(conn: AsyncConnection, document_id: UUID, citizen_id: UUID | None = None) -> dict | None:
    sql = """SELECT d.id, d.citizen_id, d.uri, d.source, d.current_version, d.first_seen_at, d.last_seen_at,
                    v.payload, (SELECT count(*) FROM document_versions WHERE document_id = d.id) AS versions_count
             FROM documents d JOIN document_versions v ON v.document_id = d.id AND v.version_no = d.current_version
             WHERE d.id = %s"""
    args: tuple = (document_id,)
    if citizen_id is not None:
        sql += " AND d.citizen_id = %s"
        args = (document_id, citizen_id)
    cur = await conn.execute(sql, args)
    return await cur.fetchone()


async def list_versions(conn: AsyncConnection, document_id: UUID) -> list[dict]:
    cur = await conn.execute(
        """SELECT version_no, content_hash, fetched_at, payload FROM document_versions
           WHERE document_id = %s ORDER BY version_no DESC""",
        (document_id,),
    )
    return await cur.fetchall()


async def list_sources(conn: AsyncConnection, citizen_id: UUID) -> list[dict]:
    cur = await conn.execute(
        "SELECT source_id, enabled, last_poll_at, last_ok_at, last_error FROM sources WHERE citizen_id = %s",
        (citizen_id,),
    )
    return await cur.fetchall()


async def session_status(conn: AsyncConnection, citizen_id: UUID, provider: str = "oneid") -> str | None:
    cur = await conn.execute(
        "SELECT status FROM source_sessions WHERE citizen_id = %s AND provider = %s", (citizen_id, provider)
    )
    row = await cur.fetchone()
    return row["status"] if row else None


async def poa_for_registry_check(conn: AsyncConnection, citizen_id: UUID) -> list[dict]:
    """Доверенности гражданина, которые ещё действуют: их сверяет vakolat.check (текущий payload нужен для наложения статуса)."""
    cur = await conn.execute(
        """SELECT d.uri, v.payload
           FROM documents d JOIN document_versions v ON v.document_id = d.id AND v.version_no = d.current_version
           WHERE d.citizen_id = %s AND d.kind IN ('poa_car', 'poa_notarial') AND d.status NOT IN ('revoked', 'expired')""",
        (citizen_id,),
    )
    return await cur.fetchall()


async def current_payloads(conn: AsyncConnection, citizen_id: UUID) -> list[dict]:
    """Текущие версии всех документов гражданина (source + payload) — для `documents sync` на другой сервер."""
    cur = await conn.execute(
        """SELECT d.source, v.payload
           FROM documents d JOIN document_versions v ON v.document_id = d.id AND v.version_no = d.current_version
           WHERE d.citizen_id = %s ORDER BY d.source, d.uri""",
        (citizen_id,),
    )
    return await cur.fetchall()
