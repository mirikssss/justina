"""Журнал аудита (Разработчик 2): shared.audit_log с цепочкой хешей.

hash = sha256(prev_hash || canonical_json({actor, action, target, at})). Правка любой строки ломает цепочку,
GET /audit/verify находит номер испорченной записи. Пишут все контексты: входы, действия, просмотры данных
родственника.
"""

from psycopg import AsyncConnection


async def write(db: AsyncConnection, *, actor: str, action: str, target: str) -> None:
    raise NotImplementedError("shared.audit.write: Разработчик 2")


async def verify(db: AsyncConnection) -> int | None:
    """None — цепочка цела, иначе seq первой испорченной записи."""
    raise NotImplementedError("shared.audit.verify: Разработчик 2")
