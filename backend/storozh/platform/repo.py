"""Таблицы «Платформы»: citizens, web_sessions, login_nonces."""

from datetime import datetime
from uuid import UUID

from psycopg import AsyncConnection


async def session_citizen(conn: AsyncConnection, token_hash: str) -> dict | None:
    cur = await conn.execute(
        """SELECT s.citizen_id, coalesce(c.lang, 'uz') AS lang
           FROM web_sessions s LEFT JOIN citizens c ON c.id = s.citizen_id
           WHERE s.token_hash = %s AND s.revoked_at IS NULL AND s.expires_at > now()""",
        (token_hash,),
    )
    return await cur.fetchone()


async def create_session(conn: AsyncConnection, citizen_id: UUID, token_hash: str, expires_at: datetime) -> None:
    await conn.execute(
        "INSERT INTO web_sessions (citizen_id, token_hash, expires_at) VALUES (%s, %s, %s)",
        (citizen_id, token_hash, expires_at),
    )


async def revoke_session(conn: AsyncConnection, token_hash: str) -> None:
    await conn.execute("UPDATE web_sessions SET revoked_at = now() WHERE token_hash = %s AND revoked_at IS NULL",
                       (token_hash,))


async def get_citizen(conn: AsyncConnection, citizen_id: UUID) -> dict | None:
    cur = await conn.execute("SELECT id, display_name, lang, pinfl_enc FROM citizens WHERE id = %s", (citizen_id,))
    return await cur.fetchone()


async def upsert_citizen(conn: AsyncConnection, citizen_id: UUID, pinfl_hmac: str, pinfl_enc: bytes,
                         display_name: str, lang: str) -> None:
    await conn.execute(
        """INSERT INTO citizens (id, pinfl_hmac, pinfl_enc, display_name, lang) VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (id) DO UPDATE SET pinfl_hmac = EXCLUDED.pinfl_hmac, pinfl_enc = EXCLUDED.pinfl_enc,
               display_name = EXCLUDED.display_name, lang = EXCLUDED.lang""",
        (citizen_id, pinfl_hmac, pinfl_enc, display_name, lang),
    )
