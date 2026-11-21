"""T5: один LISTEN на процесс будит только подписчиков нужного гражданина."""

import asyncio
import uuid

from storozh.platform.stream_hub import StreamHub
from storozh.shared import db, outbox
from tests.integration.conftest import requires_db

pytestmark = requires_db


async def test_hub_wakes_only_target_citizen_with_one_connection():
    hub = StreamHub()
    a, b = uuid.uuid4(), uuid.uuid4()
    ev_a1, ev_a2, ev_b = hub.subscribe(a), hub.subscribe(a), hub.subscribe(b)
    try:
        await asyncio.wait_for(hub.connected.wait(), 5)
        for ev in (ev_a1, ev_a2, ev_b):
            ev.clear()  # при подключении хаб будит всех — сбрасываем
        async with db.connect("documents") as conn:
            await outbox.publish(conn, type="source.session_expired", subject="source:x", citizen_id=a,
                                 data={"source": "x.y"}, dedupe_key=f"{a}:hub")
        await asyncio.wait_for(ev_a1.wait(), 5)
        assert ev_a2.is_set() and not ev_b.is_set()
        assert hub.subscribers == 3
        hub.unsubscribe(a, ev_a1)
        hub.unsubscribe(a, ev_a2)
        hub.unsubscribe(b, ev_b)
        assert hub.subscribers == 0
    finally:
        await hub.close()
