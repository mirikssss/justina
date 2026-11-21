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


async def create_nonce(conn: AsyncConnection, nonce_hash: str, expires_at: datetime) -> None:
    await conn.execute("INSERT INTO login_nonces (nonce_hash, expires_at) VALUES (%s, %s)", (nonce_hash, expires_at))


async def bind_nonce(conn: AsyncConnection, nonce_hash: str, citizen_id: UUID, chat_id_enc: bytes,
                     token_hash: str) -> bool:
    """Одна привязка на nonce: повторный /start с той же ссылкой не выдаёт второй токен."""
    cur = await conn.execute(
        """UPDATE login_nonces SET citizen_id = %s, chat_id_enc = %s, token_hash = %s
           WHERE nonce_hash = %s AND token_hash IS NULL AND used_at IS NULL AND expires_at > now()
           RETURNING nonce_hash""",
        (citizen_id, chat_id_enc, token_hash, nonce_hash),
    )
    return await cur.fetchone() is not None


async def use_login_token(conn: AsyncConnection, token_hash: str) -> UUID | None:
    cur = await conn.execute(
        """UPDATE login_nonces SET used_at = now()
           WHERE token_hash = %s AND used_at IS NULL AND expires_at > now() RETURNING citizen_id""",
        (token_hash,),
    )
    row = await cur.fetchone()
    return row["citizen_id"] if row else None


# --- T9: согласия и удаление -------------------------------------------------------------------------

async def current_consent(conn: AsyncConnection, citizen_id: UUID) -> dict | None:
    cur = await conn.execute(
        """SELECT version, scopes, accepted_at FROM consents_log
           WHERE citizen_id = %s AND withdrawn_at IS NULL ORDER BY accepted_at DESC LIMIT 1""",
        (citizen_id,),
    )
    return await cur.fetchone()


async def add_consent(conn: AsyncConnection, citizen_id: UUID, version: str, scopes: list[str]) -> dict:
    cur = await conn.execute(
        "INSERT INTO consents_log (citizen_id, version, scopes) VALUES (%s, %s, %s) RETURNING version, scopes, accepted_at",
        (citizen_id, version, scopes),
    )
    return await cur.fetchone()


async def withdraw_consents(conn: AsyncConnection, citizen_id: UUID) -> None:
    await conn.execute("UPDATE consents_log SET withdrawn_at = now() WHERE citizen_id = %s AND withdrawn_at IS NULL",
                       (citizen_id,))


async def revoke_all_sessions(conn: AsyncConnection, citizen_id: UUID) -> None:
    await conn.execute("UPDATE web_sessions SET revoked_at = now() WHERE citizen_id = %s AND revoked_at IS NULL",
                       (citizen_id,))
