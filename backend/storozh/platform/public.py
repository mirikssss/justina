"""Публичный интерфейс «Платформы»."""

from uuid import UUID

from storozh.platform import repo, service
from storozh.platform.service import LoginError
from storozh.shared import db
from storozh.shared.auth import Citizen

__all__ = ["LoginError", "bind_login", "citizen_lang", "citizen_profile", "session_citizen"]


async def bind_login(nonce: str, chat_id: int, display_name: str | None = None, lang: str = "uz") -> str:
    """Бот получил /start login_<nonce>: привязать вход к гражданину, вернуть одноразовую ссылку на /auth/callback.

    LoginError — ссылка устарела/использована или этот Telegram не привязан (бот отвечает текстом).
    """
    return await service.bind_login(nonce, chat_id, display_name, lang)


async def citizen_lang(citizen_id: UUID) -> str:
    async with db.connect("platform") as conn:
        row = await repo.get_citizen(conn, citizen_id)
    return row["lang"] if row else "uz"


async def citizen_profile(citizen_id: UUID) -> dict | None:
    """{display_name, lang, pinfl} — только для PDF-черновиков; в модель эти данные не передаются."""
    return await service.citizen_profile(citizen_id)


async def session_citizen(token_hash: str) -> Citizen | None:
    """Резолвер для shared.auth.current_citizen: действующая сессия по хешу токена из cookie."""
    async with db.connect("platform") as conn:
        row = await repo.session_citizen(conn, token_hash)
    return Citizen(id=row["citizen_id"], lang=row["lang"]) if row else None
