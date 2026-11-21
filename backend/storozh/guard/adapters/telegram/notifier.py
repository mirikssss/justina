"""Notifier для Telegram. В тексте тревоги нет ФИО, ПИНФЛ, адреса, суммы и ссылок на вход (FR-G-06).

Код и тревоги уходят только в чат, привязанный через /start link_<token> (FR-G-08). Нет привязки — NotLinked.
"""

import logging
from uuid import UUID

from storozh.guard.adapters import db as repo
from storozh.guard.adapters.telegram import messages
from storozh.guard.adapters.telegram.client import AiogramClient, TelegramClient
from storozh.guard.ports import AlertView, Notifier, NotLinked
from storozh.platform import public as platform
from storozh.shared import crypto, db
from storozh.shared.config import settings

log = logging.getLogger(__name__)


async def chat_of(citizen_id: UUID) -> int:
    async with db.connect("guard") as conn:
        link = await repo.telegram_link(conn, citizen_id)
    if link is None:
        raise NotLinked(str(citizen_id))
    return int(crypto.decrypt(citizen_id, bytes(link["chat_id_enc"])).decode())


def web_url(path: str) -> str:
    return settings.public_web_url.rstrip("/") + path


class TelegramNotifier:
    requires_link = True

    def __init__(self, client: TelegramClient | None = None):
        self.client = client or AiogramClient()

    async def send_alert(self, citizen_id: UUID, alert: AlertView) -> str:
        return await self.client.send(await chat_of(citizen_id), messages.alert_message(alert))

    async def edit_alert(self, citizen_id: UUID, message_id: str, alert: AlertView) -> None:
        await self.client.edit(await chat_of(citizen_id), message_id, messages.alert_message(alert))

    async def send_code(self, citizen_id: UUID, code: str, action_type: str = "revoke_car_poa") -> None:
        chat = await chat_of(citizen_id)
        lang = await platform.citizen_lang(citizen_id)
        await self.client.send(chat, messages.code_message(lang, code, action_type))

    async def send_action_update(self, citizen_id: UUID, action_type: str, status: str) -> None:
        reply = messages.action_update_message(await platform.citizen_lang(citizen_id), status, web_url("/alerts"))
        if reply is not None:
            await self.client.send(await chat_of(citizen_id), reply)


class LogNotifier:
    """Только ENV=dev без TELEGRAM_BOT_TOKEN: код пишется в лог, чтобы проходить сценарий без бота."""

    requires_link = False

    async def send_alert(self, citizen_id: UUID, alert: AlertView) -> str:
        log.warning("DEV alert for %s: %s %s", citizen_id, alert.rule_id, alert.title)
        return "dev"

    async def edit_alert(self, citizen_id: UUID, message_id: str, alert: AlertView) -> None:
        return None

    async def send_code(self, citizen_id: UUID, code: str, action_type: str = "revoke_car_poa") -> None:
        log.warning("DEV confirmation code for %s: %s", citizen_id, code)

    async def send_action_update(self, citizen_id: UUID, action_type: str, status: str) -> None:
        log.warning("DEV action %s for %s: %s", action_type, citizen_id, status)


_notifier: Notifier | None = None


def get_notifier() -> Notifier:
    global _notifier
    if _notifier is None:
        if settings.telegram_bot_token:
            _notifier = TelegramNotifier()
        elif settings.env == "dev":
            _notifier = LogNotifier()
        else:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is required outside ENV=dev")
    return _notifier
