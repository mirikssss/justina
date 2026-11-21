"""Процесс bot: Telegram (aiogram 3, long polling).

/start link_<token>   — привязать чат к кабинету (UC-G5)
/start login_<nonce>  — вход на сайт через бота (UC-G6) -> platform.public.bind_login
кнопки тревоги        — «Это я / Это не я»: подпись callback_data (HMAC) + проверка chat_id (FR-G-05)

on_start / on_callback — без aiogram, их проверяют тесты. Работаем только в личных чатах.
"""

import asyncio
import logging
from dataclasses import dataclass

from storozh.guard import service
from storozh.guard.adapters.telegram import callbacks, messages
from storozh.guard.adapters.telegram.messages import Reply
from storozh.guard.adapters.telegram.templates import texts
from storozh.guard.public import citizen_by_chat
from storozh.platform import public as platform
from storozh.shared.config import settings

log = logging.getLogger(__name__)


def _lang(tg_lang: str | None) -> str:
    return "ru" if (tg_lang or "").startswith("ru") else "uz"


async def on_start(chat_id: int, payload: str | None, tg_lang: str | None = None, tg_name: str | None = None) -> Reply:
    lang = _lang(tg_lang)
    payload = (payload or "").strip()
    if payload.startswith("link_"):
        result, citizen_id = await service.link_chat(payload.removeprefix("link_"), chat_id)
        if citizen_id is not None:
            lang = await platform.citizen_lang(citizen_id)
        t = texts(lang)
        return Reply({"ok": t.LINK_OK, "taken": t.LINK_TAKEN}.get(result, t.LINK_BAD))
    if payload.startswith("login_"):
        try:
            url = await platform.bind_login(payload.removeprefix("login_"), chat_id, tg_name, lang)
        except platform.LoginError:
            return Reply(texts(lang).LOGIN_BAD)
        citizen_id = await citizen_by_chat(chat_id)
        if citizen_id is not None:
            lang = await platform.citizen_lang(citizen_id)
        return messages.login_message(lang, url)
    return Reply(texts(lang).HELP)


@dataclass(frozen=True)
class CallbackResult:
    answer: str  # всплывающий ответ на нажатие
    edit: Reply | None = None  # новая версия исходного сообщения


async def on_callback(chat_id: int, data: str, tg_lang: str | None = None) -> CallbackResult:
    parsed = callbacks.verify(data)
    if parsed is None:
        log.warning("forged or broken callback_data rejected")
        return CallbackResult(texts(_lang(tg_lang)).CALLBACK_BAD)
    verdict, alert_id = parsed
    view = await service.telegram_verdict(chat_id, alert_id, verdict)
    if view is None:
        log.warning("callback for alert %s from a foreign chat rejected", alert_id)
        return CallbackResult(texts(_lang(tg_lang)).CALLBACK_BAD)
    return CallbackResult(texts(view.lang).VERDICT_DONE, messages.verdict_message(view, verdict))


async def run() -> None:
    if not settings.telegram_bot_token:
        log.warning("bot: TELEGRAM_BOT_TOKEN is empty, idling")
        await asyncio.Event().wait()

    from aiogram import Dispatcher, F, Router
    from aiogram.filters import CommandObject, CommandStart
    from aiogram.types import CallbackQuery, Message

    from storozh.guard.adapters.telegram.client import AiogramClient, markup

    client = AiogramClient()
    router = Router()
    router.message.filter(F.chat.type == "private")

    @router.message(CommandStart())
    async def start(message: Message, command: CommandObject) -> None:
        tg_lang = message.from_user.language_code if message.from_user else None
        tg_name = message.from_user.full_name if message.from_user else None
        reply = await on_start(message.chat.id, command.args, tg_lang, tg_name)
        await message.answer(reply.text, reply_markup=markup(reply), disable_web_page_preview=True)

    @router.message()
    async def other(message: Message) -> None:
        await message.answer(texts(_lang(message.from_user.language_code if message.from_user else None)).HELP)

    @router.callback_query()
    async def callback(q: CallbackQuery) -> None:
        chat = q.message.chat if q.message else None
        if chat is None or chat.type != "private":
            await q.answer()
            return
        result = await on_callback(chat.id, q.data or "", q.from_user.language_code if q.from_user else None)
        await q.answer(result.answer)
        if result.edit is not None:
            await client.edit(chat.id, str(q.message.message_id), result.edit)

    dp = Dispatcher()
    dp.include_router(router)
    log.info("bot: polling")
    await dp.start_polling(client.bot)
