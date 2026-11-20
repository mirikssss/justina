"""Нужна база с миграциями (docker compose up db migrate). Без базы тесты пропускаются."""

import uuid

import psycopg
import pytest

from storozh.shared import db, outbox
from storozh.shared.config import settings
from storozh.shared.events import Event


def _db_available() -> bool:
    try:
        with psycopg.connect(settings.database_url, connect_timeout=2) as c:
            return c.execute("SELECT to_regclass('shared.outbox')").fetchone()[0] is not None
    except psycopg.OperationalError:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="нет базы с миграциями")


@pytest.fixture(autouse=True)
async def _close_pools():
    yield
    await db.close_all()


def _event(citizen: uuid.UUID, key: str) -> Event:
    return Event.new("document.created", producer="documents", subject="uz:notarius:poa:T-1", citizen_id=citizen,
                     dedupe_key=key, data={"document_id": str(uuid.uuid4()), "version_no": 1,
                                           "kind": "poa_car", "owner_role": "principal"})


async def test_outbox_roundtrip_and_dedupe():
    citizen, key = uuid.uuid4(), f"test:{uuid.uuid4()}"
    async with db.connect("documents") as conn:
        assert await outbox.publish(conn, _event(citizen, key)) is True
        assert await outbox.publish(conn, _event(citizen, key)) is False  # тот же dedupe_key

    seen: list[Event] = []

    async def handler(ev: Event, conn) -> None:
        if ev.citizen_id == citizen:
            seen.append(ev)

    consumer = f"test-{uuid.uuid4()}"
    while await outbox.consume_once("guard", {"document.created"}, handler, consumer=consumer):
        pass
    assert [e.dedupe_key for e in seen] == [key]
    assert await outbox.consume_once("guard", {"document.created"}, handler, consumer=consumer) == 0


async def test_context_cannot_read_foreign_schema():
    async with db.connect("guard") as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            await conn.execute("SELECT 1 FROM documents.documents")


async def test_versions_are_append_only():
    async with db.connect("documents") as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            await conn.execute("UPDATE document_versions SET content_hash = 'x'")


async def test_outbox_is_append_only():
    async with db.connect("guard") as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            await conn.execute("DELETE FROM shared.outbox")
