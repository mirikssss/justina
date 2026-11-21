"""Зависимости FastAPI для аутентификации (Разработчик 2).

current_citizen читает cookie __Host-session и находит сессию по хешу токена. Таблица сессий принадлежит
«Платформе», а shared не знает о контекстах, поэтому поиск сессии регистрирует приложение при старте:
`auth.set_session_resolver(platform.public.session_citizen)` (main.py).
"""

import hashlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import HTTPException, Request

from storozh.shared import crypto
from storozh.shared.config import settings

DEV_CITIZEN_ID = UUID("00000000-0000-0000-0000-000000000001")
SESSION_COOKIE = "__Host-session"
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@dataclass(frozen=True)
class Citizen:
    id: UUID
    lang: str = "uz"


SessionResolver = Callable[[str], Awaitable[Citizen | None]]
_resolver: SessionResolver | None = None


def set_session_resolver(resolver: SessionResolver) -> None:
    global _resolver
    _resolver = resolver


def token_hash(token: str) -> str:
    """В базе храним только хеш токена сессии или одноразовой ссылки."""
    return hashlib.sha256(token.encode()).hexdigest()


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def _check_origin(request: Request) -> None:
    """CSRF: браузер на POST/PUT/DELETE шлёт Origin — он должен совпадать с нашим сайтом."""
    if request.method in _SAFE_METHODS:
        return
    origin = request.headers.get("origin")
    if origin and origin != _origin(settings.public_web_url):
        raise HTTPException(status_code=403, detail="bad origin")


async def current_citizen(request: Request) -> Citizen:
    _check_origin(request)
    token = request.cookies.get(SESSION_COOKIE)
    if token and _resolver is not None:
        citizen = await _resolver(token_hash(token))
        if citizen is not None:
            return citizen
    if settings.env == "dev":  # разработка без входа: тестовый гражданин
        return Citizen(id=DEV_CITIZEN_ID)
    raise HTTPException(status_code=401, detail="not authenticated")


async def internal_request(request: Request) -> None:
    """Внутренние эндпоинты: HMAC X-Signature + X-Timestamp (окно 5 минут).

    В dev без INGEST_HMAC_KEY подпись не проверяется. Защита от повтора — идемпотентность по snapshot_id.
    """
    if settings.env == "dev" and not settings.ingest_hmac_key:
        return
    try:
        ts = int(request.headers["x-timestamp"])
        crypto.verify_internal(await request.body(), ts, request.headers["x-signature"])
    except (KeyError, ValueError, crypto.BadSignature) as e:
        raise HTTPException(status_code=401, detail="bad signature") from e
