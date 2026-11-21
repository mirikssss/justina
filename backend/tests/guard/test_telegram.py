"""Бот без сети: подпись callback_data, тексты uz/ru, сборка сообщений (FR-G-05, FR-G-06)."""

from uuid import uuid4

import pytest

from storozh.guard.adapters.telegram import callbacks, messages
from storozh.guard.adapters.telegram.templates import ru, uz
from storozh.guard.ports import AlertView
from storozh.shared.config import settings


@pytest.fixture(autouse=True)
def _keys(monkeypatch):
    monkeypatch.setattr(settings, "callback_hmac_key", "test-callback-key")
    monkeypatch.setattr(settings, "public_web_url", "https://justina.example.uz")


def view(**kw) -> AlertView:
    base = dict(alert_id=uuid4(), rule_id="G1", severity="critical", title="t", explanation=None,
                buttons=("not_me_revoke", "me"), lang="uz",
                url="https://justina.example.uz/documents/1", object_masked="***45")
    return AlertView(**{**base, **kw})


# --- callback_data ------------------------------------------------------------------------------------

def test_callback_roundtrip_and_fits_telegram_limit():
    a = uuid4()
    for verdict in ("me", "not_me"):
        data = callbacks.sign(verdict, a)
        assert len(data.encode()) <= 64 and callbacks.verify(data) == (verdict, a)


def test_forged_callback_rejected(monkeypatch):
    a, b = uuid4(), uuid4()
    good = callbacks.sign("me", a)
    op, raw, sig = good.split(".")
    assert callbacks.verify(f"n.{raw}.{sig}") is None  # «Это я» переделали в «Это не я»
    assert callbacks.verify(f"{op}.{callbacks.sign('me', b).split('.')[1]}.{sig}") is None  # чужая тревога
    assert callbacks.verify(f"{op}.{raw}.{sig[:-1]}A") is None
    for junk in ("", "m", "m.x.y", "x.y.z.w", "m.!!!.sig", "z." + raw + "." + sig):
        assert callbacks.verify(junk) is None
    monkeypatch.setattr(settings, "callback_hmac_key", "other-key")
    assert callbacks.verify(good) is None  # подпись без ключа не подделать


# --- тексты -------------------------------------------------------------------------------------------

def test_uz_and_ru_templates_have_same_keys_and_all_rules():
    keys = lambda m: {k for k in vars(m) if k.isupper()}  # noqa: E731
    assert keys(uz) == keys(ru)
    for m in (uz, ru):
        assert set(m.ALERT) == {f"G{i}" for i in range(1, 8)}
        assert set(m.BUTTON) == {"not_me", "me", "open", "reconnect"}


# --- сообщения ----------------------------------------------------------------------------------------

def test_g1_message_has_verdict_buttons_and_card_link():
    v = view()
    reply = messages.alert_message(v)
    assert "***45" in reply.text and "Bu sizmisiz?" in reply.text
    [verdicts, links] = reply.buttons
    assert [b.label for b in verdicts] == ["Bu men emasman", "Bu men"]
    assert callbacks.verify(verdicts[0].callback) == ("not_me", v.alert_id)
    assert callbacks.verify(verdicts[1].callback) == ("me", v.alert_id)
    assert links == [messages.Button("Ochish", url=v.url)]


def test_ru_message_and_reconnect_button():
    reply = messages.alert_message(view(lang="ru", rule_id="G6", buttons=("reconnect",), object_masked=None,
                                        url="https://justina.example.uz/sources"))
    assert reply.text.startswith("🔔 Источник отключён")
    assert reply.buttons == [[messages.Button("Переподключить", url="https://justina.example.uz/sources")]]


def test_only_link_is_our_card_and_localhost_goes_to_text():
    reply = messages.alert_message(view(url="http://localhost:3000/documents/1"))
    assert all(b.callback for row in reply.buttons for b in row)  # URL-кнопки нет: Telegram её отклонит
    assert "http://localhost:3000/documents/1" in reply.text


def test_explanation_is_escaped():
    reply = messages.alert_message(view(explanation='<a href="https://evil">click</a>'))
    assert "<a href" not in reply.text and "&lt;a href" in reply.text


def test_verdict_message_drops_verdict_buttons():
    v = view()
    edited = messages.verdict_message(v, "me")
    assert uz.VERDICT_ME in edited.text and all(b.url for row in edited.buttons for b in row)


def test_code_message():
    m = messages.code_message("ru", "042517", "revoke_car_poa")
    assert "<b>042517</b>" in m.text and "отзыв доверенности" in m.text and m.buttons == []
