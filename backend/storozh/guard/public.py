"""Публичный интерфейс «Сторожа»."""

from uuid import UUID

from storozh.shared import crypto, db

__all__ = ["citizen_by_chat"]


async def citizen_by_chat(chat_id: int) -> UUID | None:
    """Гражданин, привязавший этот Telegram-чат (/start link_<token>). Нужен «Платформе» для входа на сайт."""
    async with db.connect("guard") as conn:
        cur = await conn.execute("SELECT citizen_id FROM telegram_links WHERE chat_id_hmac = %s",
                                 (crypto.hmac_chat_id(chat_id),))
        row = await cur.fetchone()
    return row["citizen_id"] if row else None
