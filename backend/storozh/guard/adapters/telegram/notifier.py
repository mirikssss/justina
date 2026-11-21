"""Notifier для Telegram. В тексте тревоги нет ФИО, ПИНФЛ, адреса, суммы и ссылок на вход (FR-G-06)."""

import logging
from uuid import UUID

from storozh.guard.ports import AlertView, Notifier
from storozh.shared.config import settings

log = logging.getLogger(__name__)


class TelegramNotifier:
    requires_link = True  # код и тревоги — только в привязанный чат (FR-G-08)

    async def send_alert(self, citizen_id: UUID, alert: AlertView) -> str:
        raise NotImplementedError("TelegramNotifier.send_alert: Разработчик 3")

    async def edit_alert(self, citizen_id: UUID, message_id: str, alert: AlertView) -> None:
        raise NotImplementedError("TelegramNotifier.edit_alert: Разработчик 3")

    async def send_code(self, citizen_id: UUID, code: str) -> None:
        raise NotImplementedError("TelegramNotifier.send_code: Разработчик 3")


class LogNotifier:
    """Только ENV=dev без TELEGRAM_BOT_TOKEN: код пишется в лог, чтобы проходить сценарий без бота."""

    requires_link = False

    async def send_alert(self, citizen_id: UUID, alert: AlertView) -> str:
        log.warning("DEV alert for %s: %s %s", citizen_id, alert.rule_id, alert.title)
        return "dev"

    async def edit_alert(self, citizen_id: UUID, message_id: str, alert: AlertView) -> None:
        return None

    async def send_code(self, citizen_id: UUID, code: str) -> None:
        log.warning("DEV confirmation code for %s: %s", citizen_id, code)


def get_notifier() -> Notifier:
    if settings.telegram_bot_token:
        return TelegramNotifier()
    if settings.env == "dev":
        return LogNotifier()
    raise RuntimeError("TELEGRAM_BOT_TOKEN is required outside ENV=dev")
