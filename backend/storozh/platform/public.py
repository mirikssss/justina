"""Публичный интерфейс «Платформы»."""

from uuid import UUID

from storozh.platform import repo
from storozh.shared import db
from storozh.shared.auth import Citizen

__all__ = ["bind_login", "citizen_lang", "session_citizen"]


async def bind_login(nonce: str, chat_id: int) -> str:
    """Бот получил /start login_<nonce>: привязать вход к гражданину, вернуть одноразовую ссылку на /auth/callback."""
    raise NotImplementedError("platform.bind_login: Разработчик 2")


async def citizen_lang(citizen_id: UUID) -> str:
    async with db.connect("platform") as conn:
        row = await repo.get_citizen(conn, citizen_id)
    return row["lang"] if row else "uz"


async def session_citizen(token_hash: str) -> Citizen | None:
    """Резолвер для shared.auth.current_citizen: действующая сессия по хешу токена из cookie."""
    async with db.connect("platform") as conn:
        row = await repo.session_citizen(conn, token_hash)
    return Citizen(id=row["citizen_id"], lang=row["lang"]) if row else None
