"""Нужна база с миграциями (docker compose up db migrate). Без базы тесты пропускаются."""

import uuid

import psycopg
import pytest

from storozh.shared import db, outbox
from storozh.shared.events import Event
from tests.integration.conftest import requires_db

pytestmark = requires_db


def _publish(conn, citizen: uuid.UUID, key: str):
    return outbox.publish(conn, type="document.created", subject="uz:notarius:poa:T-1", citizen_id=citizen,
                          dedupe_key=key, data={"document_id": str(uuid.uuid4()), "version_no": 1,
                                                "kind": "poa_car", "owner_role": "principal"})


async def test_outbox_roundtrip_and_dedupe():
    citizen, key = uuid.uuid4(), f"test:{uuid.uuid4()}"
    async with db.connect("documents") as conn:
        first = await _publish(conn, citizen, key)
        assert await _publish(conn, citizen, key) == first  # тот же dedupe_key — то же событие

    seen: list[Event] = []

    async def handler(ev: Event, conn) -> None:
        if ev.citizen_id == citizen:
            seen.append(ev)

    consumer = f"test-{uuid.uuid4()}"
    while await outbox.consume_once("guard", {"document.created"}, handler, name=consumer):
        pass
    assert [e.dedupe_key for e in seen] == [key]
    assert await outbox.consume_once("guard", {"document.created"}, handler, name=consumer) is False


async def test_failed_handler_does_not_move_cursor():
    citizen = uuid.uuid4()
    async with db.connect("documents") as conn:
        await _publish(conn, citizen, f"test:{uuid.uuid4()}")
    consumer = f"test-{uuid.uuid4()}"

    async def boom(ev: Event, conn) -> None:
        raise RuntimeError("handler failed")

    with pytest.raises(RuntimeError):
        await outbox.consume_once("guard", {"document.created"}, boom, name=consumer)
    async with db.connect("guard") as conn:
        cur = await conn.execute("SELECT last_seq FROM shared.consumer_offsets WHERE consumer = %s", (consumer,))
        assert (await cur.fetchone())["last_seq"] == 0


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
