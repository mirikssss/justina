"""Публичный интерфейс «Сторожа»."""

from uuid import UUID

from storozh.shared import crypto, db

__all__ = ["citizen_by_chat", "forget_citizen"]


async def citizen_by_chat(chat_id: int) -> UUID | None:
    """Гражданин, привязавший этот Telegram-чат (/start link_<token>). Нужен «Платформе» для входа на сайт."""
    async with db.connect("guard") as conn:
        cur = await conn.execute("SELECT citizen_id FROM telegram_links WHERE chat_id_hmac = %s",
                                 (crypto.hmac_chat_id(chat_id),))
        row = await cur.fetchone()
    return row["citizen_id"] if row else None


async def forget_citizen(citizen_id: UUID) -> None:
    """T9: «Удалить мои данные» — снять привязку Telegram: тревоги и коды больше никуда не уходят."""
    async with db.connect("guard") as conn:
        await conn.execute("DELETE FROM telegram_links WHERE citizen_id = %s", (citizen_id,))
        await conn.execute("DELETE FROM link_tokens WHERE citizen_id = %s", (citizen_id,))
