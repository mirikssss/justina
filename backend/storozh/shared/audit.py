"""Журнал аудита (Разработчик 2): shared.audit_log с цепочкой хешей.

hash = sha256(prev_hash || canonical_json({actor, action, target, at})). Правка любой строки ломает цепочку,
GET /audit/verify находит номер испорченной записи. Пишут все контексты: входы, действия, просмотры данных
родственника.
"""

import hashlib
import json
from datetime import UTC, datetime

from psycopg import AsyncConnection

GENESIS = "0" * 64
_LOCK = 0x5702_0002  # запись по одной: prev_hash всегда указывает на предыдущую строку


def _canonical_at(at: datetime) -> str:
    return at.astimezone(UTC).isoformat(timespec="microseconds")


def digest(prev_hash: str, actor: str, action: str, target: str, at: datetime) -> str:
    body = json.dumps({"actor": actor, "action": action, "target": target, "at": _canonical_at(at)},
                      sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256((prev_hash + body).encode()).hexdigest()


async def write(db: AsyncConnection, *, actor: str, action: str, target: str) -> None:
    """Дописать запись в текущей транзакции вызывающего."""
    await db.execute("SELECT pg_advisory_xact_lock(%s)", (_LOCK,))
    cur = await db.execute("SELECT hash FROM shared.audit_log ORDER BY seq DESC LIMIT 1")
    row = await cur.fetchone()
    prev = _get(row, "hash") if row else GENESIS
    at = datetime.now(UTC)
    await db.execute(
        "INSERT INTO shared.audit_log (actor, action, target, at, prev_hash, hash) VALUES (%s, %s, %s, %s, %s, %s)",
        (actor, action, target, at, prev, digest(prev, actor, action, target, at)),
    )


async def verify(db: AsyncConnection) -> int | None:
    """None — цепочка цела, иначе seq первой испорченной записи."""
    cur = await db.execute("SELECT seq, actor, action, target, at, prev_hash, hash FROM shared.audit_log ORDER BY seq")
    expected_prev = GENESIS
    async for row in cur:
        r = row if isinstance(row, dict) else dict(zip(("seq", "actor", "action", "target", "at", "prev_hash",
                                                         "hash"), row, strict=True))
        if r["prev_hash"] != expected_prev or r["hash"] != digest(r["prev_hash"], r["actor"], r["action"],
                                                                  r["target"], r["at"]):
            return r["seq"]
        expected_prev = r["hash"]
    return None


def _get(row, key: str):
    return row[key] if isinstance(row, dict) else row[0]
