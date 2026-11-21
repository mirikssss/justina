"""Процесс guard-worker: потребитель событий document.*, source.session_expired, alert.created (G7)
со своим курсором, суточная проверка сроков доверенностей (G4), исполнение подтверждённых действий."""

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from storozh.guard.service import TOPICS, daily_check, handle_event, run_next_action, sweep_actions
from storozh.shared import outbox

log = logging.getLogger(__name__)
TZ = ZoneInfo("Asia/Tashkent")
DAILY_EVERY_S = 3600  # проверка идемпотентна: запускаем раз в час, тревога G4 — одна на документ и дату
ACTIONS_IDLE_S = 1.0  # подтверждённое действие стартует ≤ 1 с (NFR-G-02: всё меньше минуты)
SWEEP_EVERY_S = 5.0


async def _daily_loop() -> None:
    while True:
        try:
            n = await daily_check(datetime.now(TZ).date())
            if n:
                log.info("daily check: %d new G4 alerts", n)
        except Exception:
            log.exception("daily check failed")
        await asyncio.sleep(DAILY_EVERY_S)


async def _actions_loop() -> None:
    """Исполнение подтверждённых действий и таймауты (код 2 мин, проверка источником 120 с)."""
    loop = asyncio.get_running_loop()
    next_sweep = 0.0
    while True:
        try:
            if loop.time() >= next_sweep:
                await sweep_actions()
                next_sweep = loop.time() + SWEEP_EVERY_S
            if await run_next_action():
                continue
        except Exception:
            log.exception("actions loop failed")
        await asyncio.sleep(ACTIONS_IDLE_S)


async def run() -> None:
    await asyncio.gather(outbox.consume("guard", TOPICS, handle_event), _daily_loop(), _actions_loop())
