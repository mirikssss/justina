"""Хелпер аудита. Таблица guard.audit_log принадлежит «Сторожу» (Разработчик 2); здесь — общая
функция записи, чтобы входы (platform) и просмотры данных родственника тоже попадали в журнал.

Цепочка хешей: hash = sha256(prev_hash || canonical_json(запись)).
"""

from typing import Any

from psycopg import AsyncConnection


async def record(conn: AsyncConnection, *, actor: str, action: str, target: str,
                 details: dict[str, Any] | None = None) -> None:
    raise NotImplementedError("shared/audit: Разработчик 2/3")
