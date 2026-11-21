"""DoD «Сторожа», шаг 2: событие -> тревога -> alert.created на живой базе (FR-G-01, FR-G-04, NFR-G-03)."""

import json
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from storozh.documents import service as documents
from storozh.guard import service
from storozh.shared import db, outbox
from storozh.shared.contracts import NormalizedDocument, SourceSnapshot
from storozh.shared.events import Event
from tests.integration.conftest import requires_db

pytestmark = requires_db
EX = Path(__file__).resolve().parents[3] / "contracts" / "examples" / "normalized_document.poa_car.json"


@pytest.fixture(autouse=True)
def _fast_explain(monkeypatch):
    async def explain(rule_id, doc, lang):
        return f"explained {rule_id}"

    monkeypatch.setattr(service.assistant, "explain_alert", explain)


def _doc(**patch) -> NormalizedDocument:
    return NormalizedDocument.model_validate({**json.loads(EX.read_text()), **patch})


async def _ingest(citizen: uuid.UUID, *docs: NormalizedDocument) -> None:
    await documents.ingest_snapshot(SourceSnapshot(snapshot_id=uuid.uuid4(), citizen_id=citizen,
                                                   source="mygov.car_poa", fetched_at=datetime.now(UTC),
                                                   complete=True, documents=list(docs)))


async def _events(citizen: uuid.UUID, types: set[str] = service.TOPICS) -> list[Event]:
    async with db.connect("guard") as conn:
        cur = await conn.execute("SELECT payload FROM shared.outbox WHERE citizen_id = %s AND type = ANY(%s)"
                                 " ORDER BY seq", (citizen, sorted(types)))
        return [Event.model_validate(r["payload"]) for r in await cur.fetchall()]


async def _handle_all(citizen: uuid.UUID, types: set[str] = service.TOPICS) -> None:
    for e in await _events(citizen, types):
        async with db.connect("guard") as conn, conn.transaction():
            await service.handle_event(e, conn)


async def _alerts(citizen: uuid.UUID) -> list[dict]:
    async with db.connect("guard") as conn:
        cur = await conn.execute("SELECT rule_id, severity, explanation, document_id, status, verdict, buttons"
                                 " FROM alerts WHERE citizen_id = %s ORDER BY created_at", (citizen,))
        return await cur.fetchall()


async def test_new_poa_raises_one_g1_alert_and_publishes_alert_created():
    citizen = uuid.uuid4()
    await _ingest(citizen, _doc())
    await _handle_all(citizen)
    await _handle_all(citizen)  # повтор событий (доставка «хотя бы раз») — без второй тревоги

    [alert] = await _alerts(citizen)
    assert alert["rule_id"] == "G1" and alert["severity"] == "critical"
    assert alert["explanation"] is None  # правила ИИ не ждут: объяснение дописывает guard.notify
    assert alert["buttons"] == ["not_me_revoke", "me"]
    [published] = await _events(citizen, {"alert.created"})
    assert published.data["rule_id"] == "G1" and published.data["document_id"] == str(alert["document_id"])
    assert published.dedupe_key.endswith(":G1")


async def test_status_change_raises_g3():
    citizen = uuid.uuid4()
    await _ingest(citizen, _doc())
    await _ingest(citizen, _doc(status="revoked"))
    await _handle_all(citizen)
    assert sorted(a["rule_id"] for a in await _alerts(citizen)) == ["G1", "G3"]


async def test_session_expired_raises_g6_without_document():
    citizen = uuid.uuid4()
    async with db.connect("documents") as conn:
        await outbox.publish(conn, type="source.session_expired", subject="source:mygov.car_poa", citizen_id=citizen,
                             data={"source": "mygov.car_poa"}, dedupe_key=f"{citizen}:expired")
    await _handle_all(citizen)
    [alert] = await _alerts(citizen)
    assert alert["rule_id"] == "G6" and alert["document_id"] is None and alert["explanation"] is None


async def _consent(grantor: uuid.UUID, grantee: uuid.UUID, scopes: list[str], revoked: bool = False) -> None:
    async with db.connect("guard") as conn:
        await conn.execute("INSERT INTO consents (grantor_id, grantee_id, scopes, revoked_at) VALUES (%s, %s, %s, %s)",
                           (grantor, grantee, scopes, datetime.now(UTC) if revoked else None))


async def test_g7_copies_critical_alert_to_relatives_with_receive_alerts_only():
    owner, relative, reader, former = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    await _consent(owner, relative, ["read_documents", "receive_alerts"])
    await _consent(owner, reader, ["read_documents"])
    await _consent(owner, former, ["receive_alerts"], revoked=True)
    await _ingest(owner, _doc())
    await _handle_all(owner)  # G1 -> alert.created
    await _handle_all(owner)  # alert.created -> G7 (и повтор — без дублей)

    [copy] = await _alerts(relative)
    assert copy["rule_id"] == "G7" and copy["severity"] == "critical" and copy["buttons"] == ["open"]
    assert await _alerts(reader) == [] and await _alerts(former) == []
    [published] = await _events(relative, {"alert.created"})
    assert published.data["rule_id"] == "G7"
    await _handle_all(relative)  # копия G7 дальше не копируется
    assert len(await _alerts(relative)) == 1


async def test_daily_check_raises_g4_once_per_expiry():
    citizen = uuid.uuid4()
    today = date(2026, 11, 21)
    await _ingest(citizen, _doc(valid_until=(today + timedelta(days=3)).isoformat()))
    await _handle_all(citizen)
    for day in (today, today, today + timedelta(days=1)):  # запуск каждый час/день — одна тревога на дату окончания
        await service.daily_check(day)
    assert [a["rule_id"] for a in await _alerts(citizen)].count("G4") == 1


async def test_verdict_me_closes_alert_and_lists_closed_last():
    citizen = uuid.uuid4()
    await _ingest(citizen, _doc())
    await _ingest(citizen, _doc(status="revoked"))
    await _handle_all(citizen)
    page = await service.list_alerts(citizen, None, 0)
    assert [a["rule_id"] for a in page["items"]] == ["G1", "G3"]  # critical раньше info
    g1 = page["items"][0]
    closed = await service.set_verdict(citizen, g1["id"], "me")
    assert closed["status"] == "closed" and closed["verdict"] == "me"
    assert [a["rule_id"] for a in (await service.list_alerts(citizen, None, 0))["items"]] == ["G3", "G1"]
    assert await service.set_verdict(uuid.uuid4(), g1["id"], "me") is None  # чужая тревога
