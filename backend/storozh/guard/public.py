"""Публичный интерфейс «Сторожа»."""

from uuid import UUID

from storozh.shared import crypto, db

__all__ = ["citizen_by_chat", "forget_citizen", "link_chat_to_citizen"]


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


async def link_chat_to_citizen(citizen_id: UUID, chat_id: int) -> None:
    """Первый вход через бота: Telegram-чат становится каналом нового гражданина (регистрация через Telegram)."""
    from storozh.guard.adapters import db as repo
    from storozh.shared import audit

    async with db.connect("guard") as conn:
        await repo.upsert_telegram_link(conn, citizen_id, crypto.encrypt(citizen_id, str(chat_id).encode()),
                                        crypto.hmac_chat_id(chat_id))
        await audit.write(conn, actor=f"citizen:{citizen_id}", action="telegram.linked", target=f"citizen:{citizen_id}")
