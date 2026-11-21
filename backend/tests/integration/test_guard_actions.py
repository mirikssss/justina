"""DoD «Сторожа», шаг 3: действие с подтверждением кодом (FR-G-07 … FR-G-11, NFR-G-03/04)."""

import json
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import pytest

from storozh.documents import service as documents
from storozh.guard import service
from storozh.guard.ports import ActionResult
from storozh.shared import crypto, db
from storozh.shared.contracts import NormalizedDocument, SourceSnapshot
from storozh.shared.events import Event
from tests.integration.conftest import requires_db

pytestmark = requires_db
EX = Path(__file__).resolve().parents[3] / "contracts" / "examples" / "normalized_document.poa_car.json"
FLOW = ["proposed", "awaiting_confirmation", "confirmed", "executing", "verifying", "done"]


class CaptureNotifier:
    requires_link = False

    def __init__(self):
        self.codes: list[tuple[uuid.UUID, str]] = []

    async def send_code(self, citizen_id, code, action_type="revoke_car_poa"):
        self.codes.append((citizen_id, code))


class FakeExecutor:
    action_type = "revoke_car_poa"

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)  # ActionResult или исключение, по одному на вызов
        self.calls = 0

    async def execute(self, req, session):
        self.calls += 1
        out = self.outcomes.pop(0)
        if isinstance(out, Exception):
            raise out
        return out


@pytest.fixture
def notifier(monkeypatch):
    n = CaptureNotifier()
    monkeypatch.setattr(service, "get_notifier", lambda: n)
    return n


@pytest.fixture(autouse=True)
def _fakes(monkeypatch):
    async def explain(rule_id, doc, lang):
        return None

    class Sessions:
        @asynccontextmanager
        async def get(self, citizen_id, provider="oneid"):
            yield object()

    async def refresh(document_id):
        return None

    monkeypatch.setattr(service.assistant, "explain_alert", explain)
    monkeypatch.setattr(service.documents, "session_provider", lambda: Sessions())
    monkeypatch.setattr(service.documents, "request_refresh", refresh)


def executor(monkeypatch, *outcomes) -> FakeExecutor:
    ex = FakeExecutor(*outcomes)
    monkeypatch.setitem(service.EXECUTORS, "revoke_car_poa", ex)
    return ex


def _doc(**patch) -> NormalizedDocument:
    return NormalizedDocument.model_validate({**json.loads(EX.read_text()), **patch})


async def _ingest(citizen: uuid.UUID, doc: NormalizedDocument) -> None:
    await documents.ingest_snapshot(SourceSnapshot(snapshot_id=uuid.uuid4(), citizen_id=citizen,
                                                   source="mygov.car_poa", fetched_at=datetime.now(UTC),
                                                   complete=True, documents=[doc]))


async def _handle_all(citizen: uuid.UUID) -> None:
    async with db.connect("guard") as conn:
        cur = await conn.execute("SELECT payload FROM shared.outbox WHERE citizen_id = %s AND type = ANY(%s)"
                                 " ORDER BY seq", (citizen, sorted(service.TOPICS)))
        events = [Event.model_validate(r["payload"]) for r in await cur.fetchall()]
    for e in events:
        async with db.connect("guard") as conn, conn.transaction():
            await service.handle_event(e, conn)


async def _setup() -> tuple[uuid.UUID, uuid.UUID]:
    citizen = uuid.uuid4()
    await _ingest(citizen, _doc())
    await _handle_all(citizen)
    async with db.connect("guard") as conn:
        cur = await conn.execute("SELECT document_id FROM poa_watch WHERE citizen_id = %s", (citizen,))
        return citizen, (await cur.fetchone())["document_id"]


def key() -> str:
    return uuid.uuid4().hex


async def _drain() -> int:
    n = 0
    while await service.run_next_action():
        n += 1
    return n


async def _action_events(action_id) -> list[str]:
    async with db.connect("guard") as conn:
        cur = await conn.execute("SELECT payload FROM shared.outbox WHERE type = 'action.updated' AND subject = %s"
                                 " ORDER BY seq", (str(action_id),))
        return [r["payload"]["data"]["status"] for r in await cur.fetchall()]


async def _set(action_id, sql: str) -> None:
    async with db.connect("guard") as conn:
        await conn.execute(f"UPDATE actions SET {sql} WHERE id = %s", (action_id,))


# --- FR-G-09: Idempotency-Key ----------------------------------------------------------------------

async def test_same_idempotency_key_returns_same_action_and_one_code(notifier):
    citizen, doc_id = await _setup()
    k = key()
    a1 = await service.create_action(citizen, doc_id, "revoke_car_poa", k)
    a2 = await service.create_action(citizen, doc_id, "revoke_car_poa", k)
    assert a1["id"] == a2["id"] and a1["status"] == "awaiting_confirmation"
    assert a1["attempts_left"] == 3 and a1["confirm_expires_at"] is not None
    assert len(notifier.codes) == 1 and notifier.codes[0][0] == citizen

    a3 = await service.create_action(citizen, doc_id, "revoke_car_poa", key())  # двойной клик с новым ключом
    assert a3["id"] == a1["id"] and len(notifier.codes) == 1


async def test_key_reuse_and_foreign_document_rejected(notifier):
    citizen, doc_id = await _setup()
    k = key()
    await service.create_action(citizen, doc_id, "revoke_car_poa", k)
    with pytest.raises(service.ActionError) as e:
        await service.create_action(uuid.uuid4(), doc_id, "revoke_car_poa", k)
    assert e.value.status == 409
    with pytest.raises(service.ActionError) as e:
        await service.create_action(uuid.uuid4(), doc_id, "revoke_car_poa", key())  # чужой документ
    assert e.value.status == 404


async def test_code_goes_only_to_linked_telegram(monkeypatch, notifier):
    notifier.requires_link = True
    citizen, doc_id = await _setup()
    with pytest.raises(service.ActionError) as e:
        await service.create_action(citizen, doc_id, "revoke_car_poa", key())
    assert e.value.status == 409 and e.value.title == "telegram_not_linked" and notifier.codes == []


# --- FR-G-08: код ------------------------------------------------------------------------------------

async def test_code_stored_as_hash_only(notifier):
    citizen, doc_id = await _setup()
    a = await service.create_action(citizen, doc_id, "revoke_car_poa", key())
    code = notifier.codes[-1][1]
    async with db.connect("guard") as conn:
        cur = await conn.execute("SELECT confirm_code_hash FROM actions WHERE id = %s", (a["id"],))
        stored = (await cur.fetchone())["confirm_code_hash"]
    assert stored and code not in stored and len(stored) == 64


async def test_three_wrong_codes_then_fourth_attempt_rejected(notifier):
    citizen, doc_id = await _setup()
    a = await service.create_action(citizen, doc_id, "revoke_car_poa", key())
    code = notifier.codes[-1][1]
    wrong = "000000" if code != "000000" else "111111"
    for left in (2, 1):
        with pytest.raises(service.ActionError) as e:
            await service.confirm_action(citizen, a["id"], wrong)
        assert e.value.status == 400 and e.value.action["attempts_left"] == left
    with pytest.raises(service.ActionError) as e:
        await service.confirm_action(citizen, a["id"], wrong)
    assert e.value.status == 429 and e.value.action["status"] == "expired"
    with pytest.raises(service.ActionError) as e:  # 4-я попытка — даже с верным кодом
        await service.confirm_action(citizen, a["id"], code)
    assert e.value.status == 429


async def test_expired_code_rejected_and_swept(notifier):
    citizen, doc_id = await _setup()
    a = await service.create_action(citizen, doc_id, "revoke_car_poa", key())
    code = notifier.codes[-1][1]
    await _set(a["id"], "confirm_expires_at = now() - interval '1 second'")
    with pytest.raises(service.ActionError) as e:
        await service.confirm_action(citizen, a["id"], code)
    assert e.value.status == 410 and e.value.action["status"] == "expired"

    b = await service.create_action(citizen, doc_id, "revoke_car_poa", key())  # новое действие можно
    assert b["id"] != a["id"]
    await _set(b["id"], "confirm_expires_at = now() - interval '1 second'")
    await service.sweep_actions()
    assert (await service.get_action(citizen, b["id"]))["status"] == "expired"


async def test_other_citizen_cannot_confirm_or_read(notifier):
    citizen, doc_id = await _setup()
    a = await service.create_action(citizen, doc_id, "revoke_car_poa", key())
    with pytest.raises(service.ActionError) as e:
        await service.confirm_action(uuid.uuid4(), a["id"], notifier.codes[-1][1])
    assert e.value.status == 404
    assert await service.get_action(uuid.uuid4(), a["id"]) is None


# --- UC-G3 целиком + NFR-G-03 -------------------------------------------------------------------------

async def test_full_flow_done_only_after_source_confirms(monkeypatch, notifier):
    citizen, doc_id = await _setup()
    shot = crypto.encrypt(citizen, b"\x89PNG fake")
    ex = executor(monkeypatch, ActionResult(ok=True, submitted=True, evidence_enc=shot))
    a = await service.create_action(citizen, doc_id, "revoke_car_poa", key())
    confirmed = await service.confirm_action(citizen, a["id"], notifier.codes[-1][1])
    again = await service.confirm_action(citizen, a["id"], notifier.codes[-1][1])  # повтор confirm
    assert confirmed["status"] == again["status"] == "confirmed"

    assert await _drain() >= 1 and ex.calls == 1
    assert (await service.get_action(citizen, a["id"]))["status"] == "verifying"
    await service.confirm_action(citizen, a["id"], notifier.codes[-1][1])  # и ещё раз — исполнения нет
    await _drain()
    assert ex.calls == 1

    await _ingest(citizen, _doc(status="revoked"))  # источник показал «аннулирована»
    await _handle_all(citizen)
    done = await service.get_action(citizen, a["id"])
    assert done["status"] == "done" and done["result"] == {"verified_status": "revoked", "error": None}
    assert [s["status"] for s in done["steps"]] == FLOW
    assert await _action_events(a["id"]) == FLOW
    assert await service.action_evidence(citizen, a["id"]) == b"\x89PNG fake"
    assert await service.action_evidence(uuid.uuid4(), a["id"]) is None


async def test_no_source_confirmation_in_120s_fails_with_evidence(monkeypatch, notifier):
    citizen, doc_id = await _setup()
    executor(monkeypatch, ActionResult(ok=True, submitted=True, evidence_enc=crypto.encrypt(citizen, b"png")))
    a = await service.create_action(citizen, doc_id, "revoke_car_poa", key())
    await service.confirm_action(citizen, a["id"], notifier.codes[-1][1])
    await _drain()
    await _set(a["id"], "updated_at = now() - interval '121 seconds'")
    await service.sweep_actions()
    failed = await service.get_action(citizen, a["id"])
    assert failed["status"] == "failed" and failed["result"]["error"] == "not_confirmed_by_source"
    assert await service.action_evidence(citizen, a["id"]) == b"png"


# --- FR-G-11 / NFR-G-04: повтор только до отправки формы ----------------------------------------------

async def _confirmed(notifier) -> tuple[uuid.UUID, dict]:
    citizen, doc_id = await _setup()
    a = await service.create_action(citizen, doc_id, "revoke_car_poa", key())
    await service.confirm_action(citizen, a["id"], notifier.codes[-1][1])
    return citizen, a


async def test_retry_once_when_failed_before_submit(monkeypatch, notifier):
    ex = executor(monkeypatch, ActionResult(ok=False, submitted=False, error="page timeout"),
                  ActionResult(ok=True, submitted=True))
    citizen, a = await _confirmed(notifier)
    await _drain()
    assert ex.calls == 2 and (await service.get_action(citizen, a["id"]))["status"] == "verifying"


async def test_no_retry_after_submit(monkeypatch, notifier):
    ex = executor(monkeypatch, ActionResult(ok=False, submitted=True, error="no success banner"),
                  ActionResult(ok=True, submitted=True))
    citizen, a = await _confirmed(notifier)
    await _drain()
    got = await service.get_action(citizen, a["id"])
    assert ex.calls == 1 and got["status"] == "failed" and got["result"]["error"] == "no success banner"


async def test_no_retry_when_executor_crashes(monkeypatch, notifier):
    ex = executor(monkeypatch, RuntimeError("browser died"), ActionResult(ok=True, submitted=True))
    citizen, a = await _confirmed(notifier)
    await _drain()
    got = await service.get_action(citizen, a["id"])
    assert ex.calls == 1 and got["status"] == "failed" and got["result"]["error"].startswith("executor_crashed")


async def test_real_executor_not_implemented_fails_honestly(notifier):
    citizen, a = await _confirmed(notifier)
    await _drain()
    got = await service.get_action(citizen, a["id"])
    assert got["status"] == "failed" and got["result"]["error"] == "executor_not_implemented"


async def test_stale_executing_action_is_failed_by_sweeper(notifier):
    citizen, a = await _confirmed(notifier)
    await _set(a["id"], "status = 'executing', updated_at = now() - interval '6 minutes'")
    await service.sweep_actions()
    assert (await service.get_action(citizen, a["id"]))["status"] == "failed"
