"""Notifier для Telegram. В тексте тревоги нет ФИО, ПИНФЛ, адреса, суммы и ссылок на вход (FR-G-06)."""

from uuid import UUID

from storozh.guard.ports import AlertView


class TelegramNotifier:
    async def send_alert(self, citizen_id: UUID, alert: AlertView) -> str:
        raise NotImplementedError("TelegramNotifier.send_alert: Разработчик 3")

    async def edit_alert(self, citizen_id: UUID, message_id: str, alert: AlertView) -> None:
        raise NotImplementedError("TelegramNotifier.edit_alert: Разработчик 3")

    async def send_code(self, citizen_id: UUID, code: str) -> None:
        raise NotImplementedError("TelegramNotifier.send_code: Разработчик 3")
