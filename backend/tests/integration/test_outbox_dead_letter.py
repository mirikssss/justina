"""T1: падающий обработчик не блокирует потребителя навсегда — после MAX_ATTEMPTS событие в dead letter."""

import uuid

from storozh.shared import db, outbox
from tests.integration.conftest import requires_db

pytestmark = requires_db


async def _publish(citizen: uuid.UUID, n: int) -> list[uuid.UUID]:
    ids = []
    async with db.connect("documents") as conn:
        for i in range(n):
            ids.append(await outbox.publish(conn, type="source.session_expired", subject=f"source:t{i}",
                                            citizen_id=citizen, data={"source": f"t.s{i}"},
                                            dedupe_key=f"{citizen}:dl:{i}"))
    return ids


async def _drain(name: str, handler) -> None:
    while True:
        try:
            if not await outbox.consume_once("guard", {"source.session_expired"}, handler, name=name):
                return
        except (ValueError, RuntimeError):  # попытка не последняя — обработчик бросил наружу
            continue


async def test_poison_event_goes_to_dead_letter_and_queue_moves_on():
    citizen = uuid.uuid4()
    name = f"test.dl.{citizen.hex[:8]}"
    poison, good = await _publish(citizen, 2)
    seen: list[uuid.UUID] = []
    calls = {"poison": 0}

    async def handler(event, conn):
        if event.citizen_id != citizen:
            return
        if event.id == poison:
            calls["poison"] += 1
            await conn.execute("INSERT INTO guard.alerts (event_id, citizen_id, rule_id, rule_version, severity, title)"
                               " VALUES (%s, %s, 'GX', 1, 'info', 'should roll back')", (event.id, citizen))
            raise ValueError("boom")
        seen.append(event.id)

    await _drain(name, handler)
    assert calls["poison"] == outbox.MAX_ATTEMPTS and seen == [good]
    async with db.connect("guard") as conn:
        cur = await conn.execute("SELECT attempts, error FROM shared.outbox_dead_letter WHERE consumer = %s", (name,))
        [dead] = await cur.fetchall()
        cur = await conn.execute("SELECT count(*) AS n FROM guard.alerts WHERE event_id = %s", (poison,))
        rolled_back = (await cur.fetchone())["n"] == 0
        cur = await conn.execute("SELECT count(*) AS n FROM shared.consumer_attempts WHERE consumer = %s", (name,))
        leftover = (await cur.fetchone())["n"]
    assert dead["attempts"] == outbox.MAX_ATTEMPTS and "boom" in dead["error"]
    assert rolled_back and leftover == 0


async def test_transient_failure_retried_without_dead_letter():
    citizen = uuid.uuid4()
    name = f"test.retry.{citizen.hex[:8]}"
    [eid] = await _publish(citizen, 1)
    calls = {"n": 0}

    async def flaky(event, conn):
        if event.id != eid:
            return
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("temporary")

    await _drain(name, flaky)
    assert calls["n"] == 3
    async with db.connect("guard") as conn:
        cur = await conn.execute("SELECT count(*) AS n FROM shared.outbox_dead_letter WHERE consumer = %s", (name,))
        assert (await cur.fetchone())["n"] == 0
