"""Порты «Сторожа». Новое действие = новая папка в adapters/actions/ + запись в белом списке.
Новый канал уведомлений = новая реализация Notifier (Telegram сейчас, push MyGov потом)."""

from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID

from storozh.documents.public import BrowserSession


@dataclass(frozen=True)
class ActionRequest:
    action_id: UUID
    citizen_id: UUID
    document_id: UUID
    type: str
    idempotency_key: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionResult:
    ok: bool
    submitted: bool  # форма отправлена: после этого повтор запрещён
    evidence_enc: bytes | None = None  # зашифрованный скриншот результата
    error: str | None = None


class ActionExecutor(Protocol):
    action_type: str  # "revoke_car_poa"

    async def execute(self, req: ActionRequest, session: BrowserSession) -> ActionResult: ...


@dataclass(frozen=True)
class AlertView:
    """То, что видит человек в уведомлении. Только безопасные поля."""

    alert_id: UUID
    rule_id: str
    severity: str
    title: str
    explanation: str | None
    buttons: tuple[str, ...]
    lang: str = "uz"


class Notifier(Protocol):
    async def send_alert(self, citizen_id: UUID, alert: AlertView) -> str: ...  # message id

    async def edit_alert(self, citizen_id: UUID, message_id: str, alert: AlertView) -> None: ...

    async def send_code(self, citizen_id: UUID, code: str) -> None: ...
