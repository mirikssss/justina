import asyncio
import logging

log = logging.getLogger(__name__)


async def run() -> None:
    # TODO(Разработчик 2): aiogram Dispatcher, /start <token>, /start login_<nonce> -> platform.public.bind_login
    log.info("bot: not implemented yet, idling")
    await asyncio.Event().wait()  # заглушка: процесс живёт, пока не реализован
