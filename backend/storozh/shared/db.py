"""Подключения к Postgres: у каждого контекста свой пул под своей ролью.

Каждое соединение делает `SET ROLE storozh_<context>` и `search_path = <context>, shared, public`.
Права роли выданы только на свою схему (см. migrations/shared/000_schemas_roles.sql), поэтому
запрос в чужую таблицу падает с permission denied, даже если кто-то его написал.

    async with db.connect("documents") as conn:
        await conn.execute("SELECT ...")
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from storozh.shared.config import settings

Context = Literal["shared", "platform", "documents", "guard", "assistant"]
CONTEXTS: tuple[Context, ...] = ("shared", "platform", "documents", "guard", "assistant")

_pools: dict[str, AsyncConnectionPool] = {}


def role_for(context: Context) -> str:
    return f"storozh_{context}"


def search_path_for(context: Context) -> str:
    return f"{context}, shared, public" if context != "shared" else "shared, public"


def _configure(context: Context):
    async def configure(conn: AsyncConnection) -> None:
        await conn.execute(f"SET ROLE {role_for(context)}")
        await conn.execute(f"SET search_path TO {search_path_for(context)}")
        await conn.commit()

    return configure


async def pool(context: Context) -> AsyncConnectionPool:
    if context not in _pools:
        p = AsyncConnectionPool(
            settings.database_url,
            min_size=1,
            max_size=8,
            kwargs={"row_factory": dict_row},
            configure=_configure(context),
            open=False,
        )
        await p.open()
        _pools[context] = p
    return _pools[context]


@asynccontextmanager
async def connect(context: Context) -> AsyncIterator[AsyncConnection]:
    """Соединение в транзакции: commit при выходе, rollback при исключении."""
    p = await pool(context)
    async with p.connection() as conn:
        yield conn


async def close_all() -> None:
    for p in _pools.values():
        await p.close()
    _pools.clear()
