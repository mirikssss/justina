"""Сценарии «Помощника»: фоновое резюме по событиям документов (FR-A-04, NFR-A-01, NFR-A-05)."""

import asyncio
import json
import logging
from uuid import UUID

from psycopg import AsyncConnection

from storozh.assistant import repo, summary
from storozh.assistant.llm.port import LLMError
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


# --------------------------------------------------------------------------- чат (FR-A-06)


async def owns_document(document_id: UUID, citizen_id: UUID) -> bool:
    async with db.connect("assistant") as conn:
        head = await repo.document_head(conn, document_id)
    return head is not None and head["citizen_id"] == citizen_id


async def chat_history(document_id: UUID, citizen_id: UUID) -> list[dict]:
    async with db.connect("assistant") as conn:
        rows = await repo.chat_history(conn, citizen_id, document_id)
    return [{**r, "id": str(r["id"]), "created_at": r["created_at"].isoformat()} for r in rows]


async def chat_events(document_id: UUID, citizen_id: UUID, message: str, lang: Lang):
    """События SSE для POST /assist/chat: token…, citations, done. Обе реплики сохраняются в историю."""
    from storozh.assistant import chat

    doc = await documents.get_document(document_id)
    async with db.connect("assistant") as conn:
        history = await repo.chat_history(conn, citizen_id, document_id, limit=chat.HISTORY_TURNS)
    result = chat.ChatResult()
    try:
        async for piece in chat.answer_stream(get_llm(), doc, message, lang, history, result):
            yield {"event": "token", "data": piece}
    except LLMError as e:
        log.warning("chat failed: %s", e)
        if not result.text:  # модель недоступна — честно говорим об этом, а не «ответа нет»
            result.text = chat.UNAVAILABLE[lang]
            yield {"event": "token", "data": result.text}
    cites = [c.model_dump() for c in result.citations]
    yield {"event": "citations", "data": json.dumps(cites, ensure_ascii=False)}
    async with db.connect("assistant") as conn:
        await repo.add_chat_message(conn, citizen_id, document_id, "user", message, [])
        await repo.add_chat_message(conn, citizen_id, document_id, "assistant", result.text, cites)
    yield {"event": "done", "data": "{}"}
