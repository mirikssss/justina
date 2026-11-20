"""Порты «Сторожа». Новое действие = новая папка в adapters/actions/ + запись в белом списке."""

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
