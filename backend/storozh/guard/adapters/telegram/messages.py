"""Сборка сообщений бота: текст (HTML) + inline-кнопки. Без сети — тестируется напрямую."""

import html
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from storozh.guard.adapters.telegram import callbacks
from storozh.guard.adapters.telegram.templates import texts
from storozh.guard.ports import AlertView


@dataclass(frozen=True)
class Button:
    label: str
    url: str | None = None
    callback: str | None = None


@dataclass(frozen=True)
class Reply:
    text: str
    buttons: list[list[Button]] = field(default_factory=list)


def url_allowed_in_button(url: str) -> bool:
    """Telegram отклоняет кнопки на localhost — тогда ссылка уходит в текст."""
    host = urlsplit(url).hostname or ""
    return urlsplit(url).scheme in ("http", "https") and host not in ("localhost", "127.0.0.1", "0.0.0.0")


def _link(reply_text: str, label: str, url: str | None, row: list[Button]) -> str:
    if not url:
        return reply_text
    if url_allowed_in_button(url):
        row.append(Button(label, url=url))
        return reply_text
    return f"{reply_text}\n\n{html.escape(label)}: {html.escape(url)}"


def alert_message(alert: AlertView) -> Reply:
    t = texts(alert.lang)
    obj = t.OBJECT.format(object=html.escape(alert.object_masked)) if alert.object_masked else ""
    text = t.ALERT.get(alert.rule_id, t.ALERT_FALLBACK).format(object=obj)
    if alert.explanation:
        text += f"\n\n{html.escape(alert.explanation)}"
    verdict_row: list[Button] = []
    if any(b.startswith("not_me") for b in alert.buttons):
        verdict_row.append(Button(t.BUTTON["not_me"], callback=callbacks.sign("not_me", alert.alert_id)))
    if "me" in alert.buttons:
        verdict_row.append(Button(t.BUTTON["me"], callback=callbacks.sign("me", alert.alert_id)))
    link_row: list[Button] = []
    label = t.BUTTON["reconnect"] if "reconnect" in alert.buttons else t.BUTTON["open"]
    text = _link(text, label, alert.url, link_row)
    return Reply(text, [r for r in (verdict_row, link_row) if r])


def verdict_message(alert: AlertView, verdict: str) -> Reply:
    """Правка исходного сообщения после ответа: кнопки вердикта убираем, ссылку оставляем."""
    t = texts(alert.lang)
    base = alert_message(alert)
    note = t.VERDICT_ME if verdict == "me" else t.VERDICT_NOT_ME
    links = [row for row in base.buttons if all(b.url for b in row)]
    return Reply(f"{base.text}\n\n<b>{html.escape(note)}</b>", links)


def code_message(lang: str, code: str, action_type: str) -> Reply:
    t = texts(lang)
    return Reply(t.CODE.format(code=html.escape(code), action=html.escape(t.ACTION.get(action_type, action_type))))


def action_update_message(lang: str, status: str, url: str | None) -> Reply | None:
    t = texts(lang)
    text = {"done": t.ACTION_DONE, "failed": t.ACTION_FAILED}.get(status)
    if text is None:
        return None
    row: list[Button] = []
    text = _link(text, t.BUTTON["open"], url, row)
    return Reply(text, [row] if row else [])


def login_message(lang: str, url: str) -> Reply:
    t = texts(lang)
    row: list[Button] = []
    text = _link(t.LOGIN_OK, t.LOGIN_BUTTON, url, row)
    return Reply(text, [row] if row else [])
