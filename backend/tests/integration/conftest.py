import os

import psycopg
import pytest

from storozh.shared import db
from storozh.shared.config import settings


def db_available() -> bool:
    try:
        with psycopg.connect(settings.database_url, connect_timeout=2) as c:
            return c.execute("SELECT to_regclass('shared.outbox')").fetchone()[0] is not None
    except psycopg.OperationalError:
        return False


# T3: в CI (REQUIRE_DB=1) отсутствие базы — ошибка, а не тихий пропуск интеграционных тестов.
if os.environ.get("REQUIRE_DB") == "1" and not db_available():
    raise RuntimeError("REQUIRE_DB=1, но базы с миграциями нет: интеграционные тесты не должны пропускаться")

requires_db = pytest.mark.skipif(not db_available(), reason="нет базы с миграциями (make db)")


@pytest.fixture(autouse=True)
async def _close_pools():
    yield
    await db.close_all()
