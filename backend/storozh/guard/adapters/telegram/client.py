"""Тонкая обёртка над Bot API (aiogram). Остальной код знает только Reply и chat_id."""

from typing import Protocol

from storozh.guard.adapters.telegram.messages import Reply
from storozh.shared.config import settings


class TelegramClient(Protocol):
    async def send(self, chat_id: int, reply: Reply) -> str: ...

    async def edit(self, chat_id: int, message_id: str, reply: Reply) -> None: ...


def markup(reply: Reply):
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    if not reply.buttons:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=b.label, url=b.url, callback_data=b.callback) for b in row]
        for row in reply.buttons
    ])


class AiogramClient:
    def __init__(self, bot=None):
        self._bot = bot

    @property
    def bot(self):
        if self._bot is None:
            from aiogram import Bot
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode

            self._bot = Bot(settings.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        return self._bot

    async def send(self, chat_id: int, reply: Reply) -> str:
        msg = await self.bot.send_message(chat_id, reply.text, reply_markup=markup(reply),
                                          disable_web_page_preview=True)
        return str(msg.message_id)

    async def edit(self, chat_id: int, message_id: str, reply: Reply) -> None:
        await self.bot.edit_message_text(reply.text, chat_id=chat_id, message_id=int(message_id),
                                         reply_markup=markup(reply), disable_web_page_preview=True)
