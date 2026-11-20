"""Мини-раннер миграций: plain SQL, по папке на контекст (storozh/migrations/<context>/NNN_*.sql).

Почему не Alembic: пять независимых владельцев схем, у Alembic это пять веток с merge-головами —
на хакатоне это больше конфликтов, чем пользы. Здесь каждый пишет SQL в свою папку, порядок —
по имени файла, учёт — в shared.schema_migrations. Применённый файл не редактируем, пишем следующий.

Запуск: python -m storozh migrate
"""

import hashlib
import logging
from pathlib import Path

import psycopg

from storozh.shared.config import settings
from storozh.shared.db import CONTEXTS, search_path_for

log = logging.getLogger(__name__)
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"

_BOOTSTRAP = """
CREATE SCHEMA IF NOT EXISTS shared;
CREATE TABLE IF NOT EXISTS shared.schema_migrations (
    context    text        NOT NULL,
    name       text        NOT NULL,
    checksum   text        NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (context, name)
);
"""


def pending() -> list[tuple[str, Path]]:
    return [(ctx, f) for ctx in CONTEXTS for f in sorted((MIGRATIONS_DIR / ctx).glob("*.sql"))]


def run(dsn: str | None = None) -> list[str]:
    applied_now: list[str] = []
    with psycopg.connect(dsn or settings.database_url, autocommit=True) as conn:
        conn.execute(_BOOTSTRAP)
        done = {(r[0], r[1]): r[2] for r in conn.execute("SELECT context, name, checksum FROM shared.schema_migrations")}
        for ctx, path in pending():
            sql = path.read_text()
            checksum = hashlib.sha256(sql.encode()).hexdigest()
            key = (ctx, path.name)
            if key in done:
                if done[key] != checksum:
                    raise RuntimeError(f"{ctx}/{path.name} changed after it was applied: write a new migration")
                continue
            with conn.transaction():
                conn.execute(f"SET LOCAL search_path TO {search_path_for(ctx)}")  # type: ignore[arg-type]
                conn.execute(sql)  # type: ignore[arg-type]
                conn.execute("INSERT INTO shared.schema_migrations (context, name, checksum) VALUES (%s, %s, %s)",
                             (ctx, path.name, checksum))
            log.info("applied %s/%s", ctx, path.name)
            applied_now.append(f"{ctx}/{path.name}")
    return applied_now
