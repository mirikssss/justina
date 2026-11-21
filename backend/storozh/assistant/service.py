"""Сценарии «Помощника»: фоновое резюме по событиям документов (FR-A-04, NFR-A-01, NFR-A-05)."""

import asyncio
import logging
from uuid import UUID

from psycopg import AsyncConnection

from storozh.assistant import repo, summary
from storozh.assistant.llm.provider import get_llm
from storozh.documents import public as documents
from storozh.shared import db, outbox
from storozh.shared.contracts import Lang
from storozh.shared.events import Event

log = logging.getLogger(__name__)

TOPICS = {"document.created", "document.changed"}
LANGS = (Lang.uz, Lang.ru)
_inflight: set[tuple[UUID, str]] = set()


async def _summarize_and_store(conn: AsyncConnection, document_id: UUID, version_no: int, citizen_id: UUID,
                               subject: str, langs: tuple[Lang, ...] = LANGS) -> None:
    todo = [lang for lang in langs if not await repo.summary_exists(conn, document_id, version_no, lang)]
    if not todo:
        return  # кэш: повтор той же версии в модель не идёт (NFR-A-05)
    doc = await documents.get_document(document_id)
    llm = get_llm()
    results = await asyncio.gather(*(summary.summarize(llm, doc, lang, document_id, version_no) for lang in todo))
    for s in results:
        body = s.model_dump(mode="json")
        if await repo.save_summary(conn, citizen_id=citizen_id, body=body, model=llm.model):
            await outbox.publish(conn, type="summary.ready", subject=subject, citizen_id=citizen_id,
                                 data={"document_id": str(document_id), "version_no": version_no, "lang": s.lang},
                                 dedupe_key=f"{document_id}:{version_no}:{s.lang}")


async def handle_event(event: Event, conn: AsyncConnection) -> None:
    """Резюме новой версии -> assistant.summaries (кэш на версию и язык) -> summary.ready."""
    document_id = UUID(event.data["document_id"])
    version_no = int(event.data["version_no"])
    log.info("summarizing", extra={"document_id": str(document_id), "version_no": version_no})
    await _summarize_and_store(conn, document_id, version_no, event.citizen_id, event.subject)


async def summarize_on_demand(document_id: UUID, citizen_id: UUID, version_no: int, subject: str,
                              lang: str) -> None:
    """Резюме ещё не посчитано (документ появился до запуска воркера): считаем в фоне, придёт summary.ready."""
    key = (document_id, lang)
    if key in _inflight:
        return
    _inflight.add(key)
    try:
        async with db.connect("assistant") as conn:
            await _summarize_and_store(conn, document_id, version_no, citizen_id, subject, (Lang(lang),))
    except Exception:
        log.exception("on-demand summary failed", extra={"document_id": str(document_id)})
    finally:
        _inflight.discard(key)


async def get_summary(document_id: UUID, citizen_id: UUID, lang: str) -> dict | None:
    """Резюме текущей версии; None — считается (запускаем расчёт, если его ещё никто не запустил).

    Бросает LookupError, если документ не найден или принадлежит другому гражданину.
    """
    async with db.connect("assistant") as conn:
        head = await repo.document_head(conn, document_id)
        if head is None or head["citizen_id"] != citizen_id:
            raise LookupError(document_id)
        body = await repo.latest_summary(conn, document_id, lang, citizen_id)
    if body is not None and body["version_no"] >= head["version_no"]:
        return body
    _tasks.add(task := asyncio.create_task(
        summarize_on_demand(document_id, citizen_id, head["version_no"], head["subject"], lang)))
    task.add_done_callback(_tasks.discard)
    return body  # старая версия лучше пустого экрана; новая придёт через summary.ready


_tasks: set[asyncio.Task] = set()
