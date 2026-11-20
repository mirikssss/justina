import asyncio
import logging

log = logging.getLogger(__name__)


async def run() -> None:
    # TODO(Разработчик 3): aiogram Dispatcher, /start link_<token>, /start login_<nonce> -> platform.public.bind_login
    log.info("bot: not implemented yet, idling")
    await asyncio.Event().wait()  # заглушка: процесс живёт, пока не реализован
