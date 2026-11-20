"""Зависимости FastAPI для аутентификации (Разработчик 2).

current_citizen читает cookie __Host-session, проверяет хеш токена в platform.web_sessions
и выставляет app.citizen_id для Row-Level Security. Пока — заглушка для разработки.
"""

from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, Request

from storozh.shared.config import settings

DEV_CITIZEN_ID = UUID("00000000-0000-0000-0000-000000000001")


@dataclass(frozen=True)
class Citizen:
    id: UUID
    lang: str = "uz"


async def current_citizen(request: Request) -> Citizen:
    # TODO(Разработчик 2): настоящая проверка сессии + SET app.citizen_id в соединении
    if settings.env == "dev":
        return Citizen(id=DEV_CITIZEN_ID)
    raise HTTPException(status_code=401, detail="not authenticated")


async def internal_request(request: Request) -> None:
    """Внутренние эндпоинты: HMAC X-Signature + X-Timestamp (окно 5 минут)."""
    # TODO(Разработчик 2): проверка подписи через crypto.verify_signature
    if settings.env != "dev":
        raise HTTPException(status_code=401, detail="bad signature")
