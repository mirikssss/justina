"""Процесс guard-worker: потребитель событий document.*, source.session_expired, alert.created (G7)
со своим курсором и суточная проверка сроков доверенностей (G4)."""

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from storozh.guard.service import TOPICS, daily_check, handle_event
from storozh.shared import outbox

log = logging.getLogger(__name__)
TZ = ZoneInfo("Asia/Tashkent")
DAILY_EVERY_S = 3600  # проверка идемпотентна: запускаем раз в час, тревога G4 — одна на документ и дату


async def _daily_loop() -> None:
    while True:
        try:
            n = await daily_check(datetime.now(TZ).date())
            if n:
                log.info("daily check: %d new G4 alerts", n)
        except Exception:
            log.exception("daily check failed")
        await asyncio.sleep(DAILY_EVERY_S)


async def run() -> None:
    await asyncio.gather(outbox.consume("guard", TOPICS, handle_event), _daily_loop())
