"""Публичный интерфейс «Платформы»."""

from uuid import UUID

__all__ = ["bind_login", "citizen_lang"]


async def bind_login(nonce: str, chat_id: int) -> str:
    """Бот получил /start login_<nonce>: привязать вход к гражданину, вернуть одноразовую ссылку на /auth/callback."""
    raise NotImplementedError("platform.bind_login: Разработчик 2")


async def citizen_lang(citizen_id: UUID) -> str:
    raise NotImplementedError("platform.citizen_lang: Разработчик 2")
