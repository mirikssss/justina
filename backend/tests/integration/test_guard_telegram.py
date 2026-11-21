"""DoD «Сторожа», шаг 4: привязка Telegram, вход через бота, кнопки тревог, уведомления (FR-G-05, UC-G1/5/6)."""

import asyncio
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from storozh.documents import service as documents
from storozh.guard import service
from storozh.guard.adapters.telegram import bot, callbacks
from storozh.guard.adapters.telegram.notifier import TelegramNotifier
from storozh.guard.adapters.telegram.templates import ru, uz
from storozh.guard.ports import NotLinked
from storozh.platform import service as platform_service
from storozh.shared import db
from storozh.shared.config import settings
from storozh.shared.contracts import NormalizedDocument, SourceSnapshot
from storozh.shared.events import Event
from tests.integration.conftest import requires_db

pytestmark = requires_db
EX = Path(__file__).resolve().parents[3] / "contracts" / "examples" / "normalized_document.poa_car.json"


class FakeClient:
    def __init__(self):
        self.sent: list[tuple[int, object]] = []
        self.edits: list[tuple[int, str, object]] = []

    async def send(self, chat_id, reply):
        self.sent.append((chat_id, reply))
        return str(len(self.sent))

    async def edit(self, chat_id, message_id, reply):
        self.edits.append((chat_id, message_id, reply))


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(settings, "callback_hmac_key", "test-callback-key")
    monkeypatch.setattr(settings, "public_web_url", "https://justina.example.uz")
    monkeypatch.setattr(service, "EXPLAIN_WAIT_S", 0.2)

    async def explain(rule_id, doc, lang):
        return f"explained {rule_id} {lang}"

    monkeypatch.setattr(service.assistant, "explain_alert", explain)


@pytest.fixture
def tg(monkeypatch) -> FakeClient:
    client = FakeClient()
    notifier = TelegramNotifier(client)
    monkeypatch.setattr(service, "get_notifier", lambda: notifier)
    return client


def chat() -> int:
    return int(uuid.uuid4().int % 10**9) + 1


async def _citizen(lang="uz") -> uuid.UUID:
    citizen = uuid.uuid4()
    await platform_service.seed_citizen(citizen, "Тест Т.", str(uuid.uuid4().int)[:14], lang)
    return citizen


async def _link(citizen: uuid.UUID, chat_id: int) -> None:
    token = (await service.create_telegram_link(citizen)).split("start=link_")[1]
    assert (await bot.on_start(chat_id, f"link_{token}")).text in (uz.LINK_OK, ru.LINK_OK)


async def _alert(citizen: uuid.UUID) -> dict:
    doc = NormalizedDocument.model_validate(json.loads(EX.read_text()))
    await documents.ingest_snapshot(SourceSnapshot(snapshot_id=uuid.uuid4(), citizen_id=citizen,
                                                   source="mygov.car_poa", fetched_at=datetime.now(UTC),
                                                   complete=True, documents=[doc]))
    for e in await _events(citizen, service.TOPICS):
        async with db.connect("guard") as conn, conn.transaction():
            await service.handle_event(e, conn)
    async with db.connect("guard") as conn:
        cur = await conn.execute("SELECT * FROM alerts WHERE citizen_id = %s AND rule_id = 'G1'", (citizen,))
        return await cur.fetchone()


async def _events(citizen: uuid.UUID, types) -> list[Event]:
    async with db.connect("guard") as conn:
        cur = await conn.execute("SELECT payload FROM shared.outbox WHERE citizen_id = %s AND type = ANY(%s)"
                                 " ORDER BY seq", (citizen, sorted(types)))
        return [Event.model_validate(r["payload"]) for r in await cur.fetchall()]


async def _notify_all(citizen: uuid.UUID) -> None:
    for e in await _events(citizen, service.NOTIFY_TOPICS):
        async with db.connect("guard") as conn, conn.transaction():
            await service.notify_event(e, conn)


async def _row(alert_id) -> dict:
    async with db.connect("guard") as conn:
        cur = await conn.execute("SELECT * FROM alerts WHERE id = %s", (alert_id,))
        return await cur.fetchone()


# --- UC-G5: привязка ------------------------------------------------------------------------------------

async def test_link_token_is_one_time_and_stored_hashed():
    citizen, chat_id = await _citizen("ru"), chat()
    link = await service.create_telegram_link(citizen)
    assert link.startswith("https://t.me/") and "start=link_" in link
    token = link.split("start=link_")[1]
    assert len(f"link_{token}") <= 64  # лимит start-параметра Telegram
    async with db.connect("guard") as conn:
        cur = await conn.execute("SELECT token_hash FROM link_tokens WHERE citizen_id = %s", (citizen,))
        assert token not in (await cur.fetchone())["token_hash"]

    assert (await bot.on_start(chat_id, f"link_{token}")).text == ru.LINK_OK  # язык кабинета
    from storozh.guard.public import citizen_by_chat
    assert await citizen_by_chat(chat_id) == citizen
    assert (await bot.on_start(chat_id, f"link_{token}", "ru")).text == ru.LINK_BAD  # повтор
    assert (await bot.on_start(chat_id, "link_nonsense")).text == uz.LINK_BAD


async def test_chat_of_another_citizen_cannot_be_hijacked():
    a, b, chat_id = await _citizen(), await _citizen(), chat()
    await _link(a, chat_id)
    token = (await service.create_telegram_link(b)).split("start=link_")[1]
    assert (await bot.on_start(chat_id, f"link_{token}")).text == uz.LINK_TAKEN
    from storozh.guard.public import citizen_by_chat
    assert await citizen_by_chat(chat_id) == a


async def test_relink_moves_citizen_to_new_chat(tg):
    citizen, old, new = await _citizen(), chat(), chat()
    await _link(citizen, old)
    await _link(citizen, new)
    await TelegramNotifier(tg).send_code(citizen, "123456")
    assert tg.sent[-1][0] == new


# --- UC-G6: вход через бота -----------------------------------------------------------------------------

async def test_login_via_bot_returns_one_time_link():
    citizen, chat_id = await _citizen("ru"), chat()
    await _link(citizen, chat_id)
    nonce = (await platform_service.start_login()).split("start=login_")[1]
    reply = await bot.on_start(chat_id, f"login_{nonce}")
    assert ru.LOGIN_OK in reply.text and "/auth/callback?token=" in (reply.buttons[0][0].url or reply.text)
    assert (await bot.on_start(chat_id, f"login_{nonce}", "ru")).text == ru.LOGIN_BAD  # nonce одноразовый


async def test_login_from_unlinked_chat_rejected_when_signup_disabled(monkeypatch):
    from storozh.shared.config import settings

    monkeypatch.setattr(settings, "telegram_signup", False)
    nonce = (await platform_service.start_login()).split("start=login_")[1]
    assert (await bot.on_start(chat(), f"login_{nonce}")).text == uz.LOGIN_BAD


async def test_start_without_payload_shows_help():
    assert (await bot.on_start(chat(), None, "ru")).text == ru.HELP


# --- кнопки: подпись и chat_id -------------------------------------------------------------------------

async def test_me_button_closes_alert_and_edits_message():
    citizen, chat_id = await _citizen(), chat()
    await _link(citizen, chat_id)
    alert = await _alert(citizen)
    result = await bot.on_callback(chat_id, callbacks.sign("me", alert["id"]))
    assert result.answer == uz.VERDICT_DONE and uz.VERDICT_ME in result.edit.text
    assert all(b.url for row in result.edit.buttons for b in row)  # кнопок вердикта больше нет
    row = await _row(alert["id"])
    assert row["verdict"] == "me" and row["status"] == "closed"


async def test_forged_callback_rejected_and_alert_untouched():
    citizen, chat_id = await _citizen(), chat()
    await _link(citizen, chat_id)
    alert = await _alert(citizen)
    good = callbacks.sign("me", alert["id"])
    forged = "n" + good[1:]  # подменили «Это я» на «Это не я», подпись старая
    result = await bot.on_callback(chat_id, forged)
    assert result.answer == uz.CALLBACK_BAD and result.edit is None
    assert (await _row(alert["id"]))["verdict"] is None


async def test_valid_callback_from_foreign_chat_rejected():
    citizen, chat_id, stranger = await _citizen(), chat(), chat()
    await _link(citizen, chat_id)
    alert = await _alert(citizen)
    result = await bot.on_callback(stranger, callbacks.sign("not_me", alert["id"]))
    assert result.answer == uz.CALLBACK_BAD and (await _row(alert["id"]))["verdict"] is None


# --- UC-G1: уведомления ---------------------------------------------------------------------------------

async def test_alert_sent_to_linked_chat_once_with_explanation(tg):
    citizen, chat_id = await _citizen("ru"), chat()
    await _link(citizen, chat_id)
    alert = await _alert(citizen)
    await _notify_all(citizen)
    await _notify_all(citizen)  # повтор alert.created — второго сообщения нет
    [(to, reply)] = tg.sent
    assert to == chat_id and reply.text.startswith("⚠️ От вашего имени выдана доверенность")
    assert "explained G1 ru" in reply.text
    assert reply.buttons[1][0].url == f"https://justina.example.uz/documents/{alert['document_id']}"
    row = await _row(alert["id"])
    assert row["tg_message_id"] == "1" and row["explanation"] == "explained G1 ru"


async def test_slow_explanation_sends_template_then_edits(tg, monkeypatch):
    async def slow(rule_id, doc, lang):
        await asyncio.sleep(0.5)
        return "late explanation"

    monkeypatch.setattr(service.assistant, "explain_alert", slow)
    citizen, chat_id = await _citizen(), chat()
    await _link(citizen, chat_id)
    alert = await _alert(citizen)
    await _notify_all(citizen)
    [(_, sent)] = tg.sent
    assert "late explanation" not in sent.text  # шаблон ушёл, не дожидаясь ИИ
    [(to, message_id, edited)] = tg.edits
    assert to == chat_id and message_id == "1" and "late explanation" in edited.text
    assert (await _row(alert["id"]))["explanation"] == "late explanation"


async def test_unlinked_citizen_gets_no_message_but_explanation_saved(tg):
    citizen = await _citizen()
    alert = await _alert(citizen)
    await _notify_all(citizen)
    assert tg.sent == []
    row = await _row(alert["id"])
    assert row["tg_message_id"] is None and row["explanation"] == "explained G1 uz"


async def test_code_only_to_linked_chat(tg):
    citizen = await _citizen()
    with pytest.raises(NotLinked):
        await TelegramNotifier(tg).send_code(citizen, "123456")
    chat_id = chat()
    await _link(citizen, chat_id)
    await TelegramNotifier(tg).send_code(citizen, "123456")
    assert tg.sent[-1][0] == chat_id and "<b>123456</b>" in tg.sent[-1][1].text


async def test_action_done_notifies_chat(tg):
    citizen, chat_id = await _citizen("ru"), chat()
    await _link(citizen, chat_id)
    e = Event.new("action.updated", subject=str(uuid.uuid4()), citizen_id=citizen, dedupe_key=str(uuid.uuid4()),
                  data={"action_id": str(uuid.uuid4()), "type": "revoke_car_poa", "status": "done"})
    async with db.connect("guard") as conn:
        await service.notify_event(e, conn)
    assert tg.sent[-1][1].text.startswith(ru.ACTION_DONE)


# --- T2: идемпотентная отправка; T11: задержки ---------------------------------------------------------

async def test_interrupted_send_is_not_repeated_blindly(tg):
    citizen, chat_id = await _citizen(), chat()
    await _link(citizen, chat_id)
    alert = await _alert(citizen)
    async with db.connect("guard") as conn:  # прошлая попытка застолбила отправку и упала до записи результата
        await conn.execute("INSERT INTO notify_log (key, status) VALUES (%s, 'sending')", (f"alert:{alert['id']}",))
    await _notify_all(citizen)
    assert tg.sent == []  # лучше потерять одно сообщение, чем прислать два


async def test_failed_send_marked_and_not_retried_forever(tg, monkeypatch):
    citizen, chat_id = await _citizen(), chat()
    await _link(citizen, chat_id)
    alert = await _alert(citizen)

    async def down(chat_id, reply):
        raise ConnectionError("telegram down")

    monkeypatch.setattr(tg, "send", down)
    await _notify_all(citizen)  # не бросает: очередь уведомлений не встаёт
    async with db.connect("guard") as conn:
        cur = await conn.execute("SELECT status FROM notify_log WHERE key = %s", (f"alert:{alert['id']}",))
        assert (await cur.fetchone())["status"] == "skipped"


async def test_latency_timestamps_recorded(tg):
    citizen, chat_id = await _citizen(), chat()
    await _link(citizen, chat_id)
    alert = await _alert(citizen)
    [created] = [e for e in await _events(citizen, {"document.created"})]
    await _notify_all(citizen)
    row = await _row(alert["id"])
    assert row["detected_at"] == created.occurred_at
    assert row["sent_at"] is not None and row["sent_at"] >= row["detected_at"]
    page = await service.list_alerts(citizen, None, 0)
    assert page["items"][0]["sent_at"] == row["sent_at"]
