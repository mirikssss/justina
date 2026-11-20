"""Синхронный пул для RAG-кода (corpus/retrieval написаны синхронно, FastAPI гоняет их в threadpool).

Те же правила, что у shared/db.py: роль storozh_assistant и search_path на схему assistant.
"""

import atexit
from contextlib import contextmanager

from pgvector.psycopg import register_vector
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from storozh.shared.config import settings
from storozh.shared.db import role_for, search_path_for

_pool: ConnectionPool | None = None


def _configure(conn: Connection) -> None:
    conn.execute(f"SET ROLE {role_for('assistant')}")
    conn.execute(f"SET search_path TO {search_path_for('assistant')}")
    conn.commit()
    register_vector(conn)


def pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            settings.database_url,
            min_size=1,
            max_size=8,
            kwargs={"row_factory": dict_row},
            configure=_configure,
            open=True,
        )
        atexit.register(_pool.close)
    return _pool


@contextmanager
def connection():
    with pool().connection() as conn:
        yield conn
