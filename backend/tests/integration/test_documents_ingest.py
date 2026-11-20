"""DoD «Документов»: версии и события на живой базе."""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from storozh.documents import service
from storozh.shared import db
from storozh.shared.contracts import NormalizedDocument, SourceSnapshot
from tests.integration.conftest import requires_db

pytestmark = requires_db
EX = Path(__file__).resolve().parents[3] / "contracts" / "examples" / "normalized_document.poa_car.json"


def _doc(**patch) -> NormalizedDocument:
    return NormalizedDocument.model_validate({**json.loads(EX.read_text()), **patch})


def _snap(citizen: uuid.UUID, docs: list[NormalizedDocument], complete: bool = True) -> SourceSnapshot:
    return SourceSnapshot(snapshot_id=uuid.uuid4(), citizen_id=citizen, source="mygov.car_poa",
                          fetched_at=datetime.now(UTC), complete=complete, documents=docs)


async def _events(citizen: uuid.UUID) -> list[str]:
    async with db.connect("documents") as conn:
        cur = await conn.execute("SELECT type FROM shared.outbox WHERE citizen_id = %s ORDER BY seq", (citizen,))
        return [r["type"] for r in await cur.fetchall()]


async def test_created_then_same_snapshot_is_noop():
    citizen = uuid.uuid4()
    snap = _snap(citizen, [_doc()])
    assert await service.ingest_snapshot(snap) == {"new_versions": 1}
    assert await service.ingest_snapshot(snap) == {"new_versions": 0}  # повтор snapshot_id
    assert await service.ingest_snapshot(_snap(citizen, [_doc()])) == {"new_versions": 0}  # тот же хеш
    assert await _events(citizen) == ["document.created"]


async def test_status_change_creates_version_and_two_events():
    citizen = uuid.uuid4()
    await service.ingest_snapshot(_snap(citizen, [_doc()]))
    await service.ingest_snapshot(_snap(citizen, [_doc(status="revoked")]))
    assert await _events(citizen) == ["document.created", "document.changed", "document.status_changed"]

    feed = await service.list_documents(citizen)
    [item] = feed["items"]
    assert item["status"] == "revoked" and item["counterparty_masked"] == "Б***р К."
    versions = await service.list_versions(item["id"], citizen)
    assert [v["version_no"] for v in versions] == [2, 1] and versions[0]["changed_fields"] == ["status"]
    assert await service.version_diff(item["id"], 2, citizen) == [{"field": "status", "from": "active",
                                                                   "to": "revoked"}]


async def test_disappeared_after_two_complete_snapshots():
    citizen = uuid.uuid4()
    await service.ingest_snapshot(_snap(citizen, [_doc()]))
    await service.ingest_snapshot(_snap(citizen, [], complete=False))  # неполный — не считается
    await service.ingest_snapshot(_snap(citizen, []))
    assert "document.disappeared" not in await _events(citizen)
    await service.ingest_snapshot(_snap(citizen, []))
    await service.ingest_snapshot(_snap(citizen, []))  # третий раз — без повторного события
    assert (await _events(citizen)).count("document.disappeared") == 1
    [item] = (await service.list_documents(citizen))["items"]
    assert item["status"] == "active"  # статус не меняется


async def test_other_citizen_does_not_see_document():
    citizen = uuid.uuid4()
    await service.ingest_snapshot(_snap(citizen, [_doc()]))
    [item] = (await service.list_documents(citizen))["items"]
    assert (await service.list_documents(uuid.uuid4()))["items"] == []
    try:
        await service.get_document_detail(item["id"], uuid.uuid4())
    except service.NotFound:
        pass
    else:
        raise AssertionError("чужой документ отдан")


async def test_payload_has_no_raw_personal_data():
    citizen = uuid.uuid4()
    await service.ingest_snapshot(_snap(citizen, [_doc()]))
    async with db.connect("documents") as conn:
        cur = await conn.execute(
            """SELECT v.payload::text AS p FROM document_versions v JOIN documents d ON d.id = v.document_id
               WHERE d.citizen_id = %s""", (citizen,))
        text = " ".join(r["p"] for r in await cur.fetchall())
    import re
    assert not re.search(r"\b\d{14}\b", text)  # ПИНФЛ
    assert not re.search(r"\b[A-Z]{2}\d{7}\b", text)  # паспорт
    assert not re.search(r"\+?998\d{9}", text)  # телефон


async def test_session_provider_serializes_access(monkeypatch):
    """FR-D-11: пока одна сессия в работе, вторая ждёт."""
    import asyncio

    from storozh.shared import crypto

    monkeypatch.setattr(crypto, "encrypt", lambda cid, b: b)
    monkeypatch.setattr(crypto, "decrypt", lambda cid, b: bytes(b))
    citizen = uuid.uuid4()
    await service.save_session(citizen, {"cookies": []})
    provider = service.session_provider()
    order: list[str] = []

    async def use(name: str, hold: float) -> None:
        async with provider.get(citizen) as session:
            assert session.storage_state == {"cookies": []}
            order.append(f"{name}+")
            await asyncio.sleep(hold)
            order.append(f"{name}-")

    await asyncio.gather(use("a", 0.3), use("b", 0))
    assert order in (["a+", "a-", "b+", "b-"], ["b+", "b-", "a+", "a-"])

    await service.expire_session(citizen)
    assert "source.session_expired" in await _events(citizen)
    statuses = {s["source_id"]: s["status"] for s in await service.list_sources(citizen)}
    assert set(statuses.values()) == {"expired"}
