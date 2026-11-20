"""Процесс collector: опрос источников по расписанию и отправка SourceSnapshot в Ingestion API.

Сборщик не пишет в базу напрямую — только POST /internal/ingest/snapshots. В целевом состоянии
тот же контракт шлёт шина межведомственной интеграции MyGov.
"""

import asyncio
import logging

from storozh.documents.adapters import ADAPTERS

log = logging.getLogger(__name__)


async def run() -> None:
    log.info("collector: adapters %s", [a.source_id for a in ADAPTERS])
    # TODO(Разработчик 1): APScheduler, вежливый опрос (лимит, ±3 с, экспоненциальная пауза), проверка сессий
    await asyncio.Event().wait()  # заглушка: процесс живёт, пока не реализован
