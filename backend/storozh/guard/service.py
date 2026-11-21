"""Сценарии «Сторожа»: событие -> тревога -> подтверждённое действие -> проверка по источнику."""

import asyncio
import logging
from datetime import date, timedelta
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from psycopg import AsyncConnection

from storozh.assistant import public as assistant
from storozh.documents import public as documents
from storozh.guard.adapters import db as repo
from storozh.guard.domain.rules import DAILY_CHECK, RuleContext, evaluate
from storozh.guard.domain.rules.base import POA_KINDS
from storozh.guard.domain.rules.g4_poa_expiring import WINDOW_DAYS
from storozh.shared import audit, db, outbox
from storozh.shared.contracts import NormalizedDocument
from storozh.shared.events import Event

log = logging.getLogger(__name__)

TOPICS = {"document.created", "document.changed", "document.status_changed", "document.disappeared",
          "source.session_expired", "alert.created"}
EXPLAIN_TIMEOUT_S = 5.0  # FR-G-04: тревога не ждёт ИИ дольше 5 с
_DAILY_NS = uuid5(NAMESPACE_URL, "storozh:guard:daily_check")


async def _explain(rule_id: str, doc: NormalizedDocument | None, lang: str = "uz") -> str | None:
    if doc is None:
        return None
    try:
        return await asyncio.wait_for(assistant.explain_alert(rule_id, doc, lang), EXPLAIN_TIMEOUT_S)
    except Exception as e:  # таймаут, нет ключа модели и т. п. — шаблон, тревога важнее объяснения
        log.warning("explain_alert skipped for %s: %s", rule_id, e)
        return None


async def _raise_alerts(conn: AsyncConnection, event: Event, doc: NormalizedDocument | None,
                        document_id: UUID | None, ctx: RuleContext, citizen_id: UUID | None = None) -> int:
    """Правила -> guard.alerts -> alert.created в той же транзакции. Возвращает число новых тревог."""
    citizen_id = citizen_id or event.citizen_id
    created = 0
    for draft in evaluate(event, doc, ctx):
        explanation = await _explain(draft.rule_id, doc)
        alert_id = await repo.insert_alert(conn, event_id=event.id, citizen_id=citizen_id, document_id=document_id,
                                           draft=draft, explanation=explanation)
        if alert_id is None:
            continue  # повтор события
        # G7 даёт несколько копий на одно событие — в ключ входит получатель
        dedupe = f"{event.id}:{draft.rule_id}" if citizen_id == event.citizen_id \
            else f"{event.id}:{draft.rule_id}:{citizen_id}"
        await outbox.publish(conn, type="alert.created", subject=str(alert_id), citizen_id=citizen_id,
                             data={"alert_id": str(alert_id), "rule_id": draft.rule_id,
                                   "severity": str(draft.severity),
                                   "document_id": str(document_id) if document_id else None,
                                   "rule_version": draft.rule_version},
                             dedupe_key=dedupe)
        log.info("alert created", extra={"alert_id": str(alert_id), "rule_id": draft.rule_id})
        created += 1
    return created


async def _load_document(document_id: UUID | None) -> NormalizedDocument | None:
    if document_id is None:
        return None
    try:
        return await documents.get_document(document_id)
    except LookupError:
        log.warning("document not found", extra={"document_id": str(document_id)})
        return None


def _document_id(data: dict[str, Any]) -> UUID | None:
    raw = data.get("document_id")
    return UUID(raw) if raw else None


async def handle_event(event: Event, conn: AsyncConnection) -> None:
    """Правила -> guard.alerts (unique по событию, правилу и получателю) -> alert.created."""
    document_id = _document_id(event.data)

    if event.type == "alert.created":  # G7: копии critical-тревог родственникам
        if event.data.get("severity") != "critical" or event.data.get("rule_id") == "G7":
            return
        for grantee in await repo.receive_alerts_grantees(conn, event.citizen_id):
            await _raise_alerts(conn, event, None, document_id, RuleContext(family_consent=True), citizen_id=grantee)
        return

    doc = await _load_document(document_id)
    if doc is not None and document_id is not None and doc.kind in POA_KINDS:
        status = "disappeared" if event.type == "document.disappeared" else str(doc.status)
        await repo.upsert_poa_watch(conn, document_id=document_id, citizen_id=event.citizen_id,
                                    valid_until=doc.valid_until, status=status)
    await _raise_alerts(conn, event, doc, document_id, RuleContext())


def daily_check_event(document_id: UUID, citizen_id: UUID, subject: str, valid_until: date) -> Event:
    """Внутреннее событие G4. id детерминирован: одна тревога на документ и дату окончания, сколько ни запускай."""
    key = f"{document_id}:{valid_until.isoformat()}"
    return Event(id=uuid5(_DAILY_NS, key), type=DAILY_CHECK, schema=f"{DAILY_CHECK}/v1", producer="guard",
                 subject=subject, citizen_id=citizen_id, dedupe_key=f"daily:{key}",
                 data={"document_id": str(document_id)})


async def daily_check(today: date) -> int:
    """G4: доверенности, истекающие в ближайшие 7 дней. Идемпотентно — можно запускать хоть каждый час."""
    created = 0
    async with db.connect("guard") as conn:
        for row in await repo.expiring_poas(conn, today, today + timedelta(days=WINDOW_DAYS)):
            doc = await _load_document(row["document_id"])
            if doc is None:
                continue
            event = daily_check_event(row["document_id"], row["citizen_id"], doc.uri, row["valid_until"])
            created += await _raise_alerts(conn, event, doc, row["document_id"], RuleContext(today=today))
    return created


# --- чтение тревог для API -------------------------------------------------------------------------

def alert_out(row: dict[str, Any]) -> dict[str, Any]:
    return {**row, "buttons": list(row["buttons"] or [])}


async def list_alerts(citizen_id: UUID, status: str | None, offset: int, limit: int = 50) -> dict[str, Any]:
    async with db.connect("guard") as conn:
        rows = await repo.list_alerts(conn, citizen_id, status=status, offset=offset, limit=limit + 1)
    more = len(rows) > limit
    return {"items": [alert_out(r) for r in rows[:limit]], "next_offset": offset + limit if more else None}


async def document_alerts(citizen_id: UUID, document_id: UUID) -> list[dict[str, Any]]:
    async with db.connect("guard") as conn:
        return [alert_out(r) for r in await repo.document_alerts(conn, citizen_id, document_id)]


async def set_verdict(citizen_id: UUID, alert_id: UUID, verdict: str) -> dict[str, Any] | None:
    async with db.connect("guard") as conn:
        row = await repo.set_verdict(conn, citizen_id, alert_id, verdict)
        if row is None:
            return None
        await audit.write(conn, actor=f"citizen:{citizen_id}", action=f"alert.verdict.{verdict}",
                          target=f"alert:{alert_id}")
    return alert_out(row)
