"""Сценарии «Сторожа»: событие -> тревога -> подтверждённое действие -> проверка по источнику."""

import asyncio
import base64
import hashlib
import hmac
import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from psycopg import AsyncConnection

from storozh.assistant import public as assistant
from storozh.documents import public as documents
from storozh.guard.adapters import db as repo
from storozh.guard.adapters.actions import EXECUTORS
from storozh.guard.adapters.telegram.notifier import get_notifier
from storozh.guard.domain.actions import (
    ACTION_TYPES,
    CODE_TTL,
    EXECUTING_STALE,
    MAX_ATTEMPTS,
    VERIFY_TIMEOUT,
    ActionStatus,
    Confirm,
    can_transition,
    code_matches,
    hash_code,
    judge_confirm,
    new_code,
)
from storozh.guard.domain.rules import DAILY_CHECK, RuleContext, evaluate
from storozh.guard.domain.rules.base import POA_KINDS
from storozh.guard.domain.rules.g4_poa_expiring import WINDOW_DAYS
from storozh.guard.ports import ActionRequest, ActionResult
from storozh.shared import audit, crypto, db, outbox
from storozh.shared.config import settings
from storozh.shared.contracts import DocumentKind, NormalizedDocument
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
    await _close_verified_actions(conn, event, document_id)
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


# --- действия: подтверждение, исполнение, проверка по источнику (FR-G-07 … FR-G-11) --------------------

class ActionError(Exception):
    """Ошибка сценария действия -> problem+json с этим статусом."""

    def __init__(self, status: int, title: str, action: dict[str, Any] | None = None):
        super().__init__(title)
        self.status, self.title, self.action = status, title, action


SYSTEM = "system:guard"


def _code_key() -> bytes:
    if not settings.master_key:
        raise ActionError(500, "MASTER_KEY is not configured")
    return hmac.new(base64.b64decode(settings.master_key), b"guard:confirm-code", hashlib.sha256).digest()


async def _transition(conn: AsyncConnection, action: dict[str, Any], dst: ActionStatus, *, actor: str,
                      **fields: Any) -> dict[str, Any]:
    """Единственный путь смены статуса: проверка автомата, шаг хода, аудит, action.updated — одной транзакцией."""
    src = ActionStatus(action["status"])
    if not can_transition(src, dst):
        raise ActionError(409, f"action cannot go {src} -> {dst}", action)
    row = await repo.update_action(conn, action["id"], expect_status=src, status=dst, **fields)
    if row is None:
        raise ActionError(409, "action changed concurrently", action)
    await _record_step(conn, row, actor)
    return row


async def _record_step(conn: AsyncConnection, row: dict[str, Any], actor: str) -> None:
    status = row["status"]
    await repo.add_step(conn, row["id"], status)
    await audit.write(conn, actor=actor, action=f"action.{status}", target=f"action:{row['id']}")
    error = (row["result"] or {}).get("error")
    await outbox.publish(conn, type="action.updated", subject=str(row["id"]), citizen_id=row["citizen_id"],
                         data={"action_id": str(row["id"]), "type": row["type"], "status": status,
                               "document_id": str(row["document_id"]), "error": error},
                         dedupe_key=f"{row['id']}:{status}")


async def action_view(conn: AsyncConnection, row: dict[str, Any]) -> dict[str, Any]:
    """Action из contracts/openapi.yaml. Хеш кода и скриншот наружу не уходят."""
    awaiting = row["status"] == ActionStatus.awaiting_confirmation
    return {
        "id": row["id"], "type": row["type"], "document_id": row["document_id"], "status": row["status"],
        "steps": await repo.action_steps(conn, row["id"]),
        "attempts_left": max(0, MAX_ATTEMPTS - row["attempts"]),
        "confirm_expires_at": row["confirm_expires_at"] if awaiting else None,
        "result": row["result"],
    }


async def create_action(citizen_id: UUID, document_id: UUID, type: str, idempotency_key: str) -> dict[str, Any]:
    """Шаг 1 (UC-G3): действие -> awaiting_confirmation, код уходит в привязанный Telegram.

    Повтор с тем же Idempotency-Key возвращает то же действие (FR-G-09) и второго кода не шлёт.
    """
    if type not in ACTION_TYPES:
        raise ActionError(422, f"action type {type!r} is not allowed")
    notifier = get_notifier()
    code: str | None = None
    async with db.connect("guard") as conn:
        same = await repo.action_by_key(conn, idempotency_key)
        if same is not None:
            if (same["citizen_id"], same["document_id"], same["type"]) != (citizen_id, document_id, type):
                raise ActionError(409, "Idempotency-Key already used for another request")
            return await action_view(conn, same)

        watch = await repo.get_poa_watch(conn, document_id)
        if watch is None or watch["citizen_id"] != citizen_id:
            raise ActionError(404, "document not found")
        if watch["status"] != "active":
            raise ActionError(409, "document is not active")
        doc = await _load_document(document_id)
        if doc is None or doc.kind != DocumentKind.poa_car:
            raise ActionError(422, "revoke_car_poa works only for car powers of attorney")
        if getattr(notifier, "requires_link", True) and not await repo.has_telegram_link(conn, citizen_id):
            raise ActionError(409, "telegram_not_linked")

        opened = await repo.open_action(conn, document_id, type)
        if opened is not None:  # двойной клик с новым ключом: второго отзыва не будет
            if opened["citizen_id"] != citizen_id:
                raise ActionError(404, "document not found")
            return await action_view(conn, opened)

        row = await repo.insert_action(conn, citizen_id=citizen_id, document_id=document_id, type=type,
                                       alert_id=await repo.latest_alert_id(conn, citizen_id, document_id),
                                       idempotency_key=idempotency_key)
        if row is None:  # параллельный запрос успел первым
            raise ActionError(409, "action is being created, retry")
        actor = f"citizen:{citizen_id}"
        await _record_step(conn, row, actor)
        code = new_code()
        row = await _transition(conn, row, ActionStatus.awaiting_confirmation, actor=actor,
                                confirm_code_hash=hash_code(_code_key(), row["id"], code),
                                confirm_expires_at=datetime.now(UTC) + CODE_TTL)
        view = await action_view(conn, row)
    # Код — после коммита: в Telegram не уйдёт код от действия, которого нет в базе.
    try:
        await notifier.send_code(citizen_id, code)
    except Exception as e:
        log.exception("confirmation code not delivered", extra={"action_id": str(row["id"])})
        async with db.connect("guard") as conn:
            current = await repo.get_action(conn, row["id"], for_update=True)
            if current and current["status"] == ActionStatus.awaiting_confirmation:
                await _transition(conn, current, ActionStatus.failed, actor=SYSTEM,
                                  confirm_code_hash=None, result={"verified_status": None,
                                                                  "error": "code_not_delivered"})
        raise ActionError(502, "confirmation code not delivered") from e
    return view


async def confirm_action(citizen_id: UUID, action_id: UUID, code: str) -> dict[str, Any]:
    """Шаг 2: код. Неверный — 400; третий неверный и дальше — 429; через 2 минуты — 410 (FR-G-08)."""
    error: ActionError | None = None
    async with db.connect("guard") as conn:
        row = await repo.get_action(conn, action_id, citizen_id, for_update=True)
        if row is None:
            raise ActionError(404, "action not found")
        status = ActionStatus(row["status"])
        ok = code_matches(_code_key(), row["id"], code, row["confirm_code_hash"])
        verdict = judge_confirm(status, row["attempts"], row["confirm_expires_at"], datetime.now(UTC), ok)
        actor = f"citizen:{citizen_id}"
        if verdict == Confirm.accept:
            row = await _transition(conn, row, ActionStatus.confirmed, actor=actor, confirm_code_hash=None)
        elif verdict == Confirm.wrong:
            row = await repo.update_action(conn, row["id"], expect_status=status,
                                           attempts=row["attempts"] + 1) or row
            await audit.write(conn, actor=actor, action="action.code_wrong", target=f"action:{action_id}")
            error = ActionError(400, "wrong code")
        elif verdict == Confirm.exhausted:
            if status == ActionStatus.awaiting_confirmation:
                row = await _transition(conn, row, ActionStatus.expired, actor=actor, confirm_code_hash=None,
                                        attempts=max(row["attempts"] + 1, MAX_ATTEMPTS))
            error = ActionError(429, "too many attempts")
        elif verdict == Confirm.timeout:
            if status == ActionStatus.awaiting_confirmation:
                row = await _transition(conn, row, ActionStatus.expired, actor=SYSTEM, confirm_code_hash=None)
            error = ActionError(410, "confirmation code expired")
        elif verdict == Confirm.closed:
            error = ActionError(409, "action is closed")
        view = await action_view(conn, row)
    if error is not None:  # попытка и истечение уже закоммичены — только теперь отказ
        error.action = view
        raise error
    return view


async def get_action(citizen_id: UUID, action_id: UUID) -> dict[str, Any] | None:
    async with db.connect("guard") as conn:
        row = await repo.get_action(conn, action_id, citizen_id)
        return await action_view(conn, row) if row else None


async def action_evidence(citizen_id: UUID, action_id: UUID) -> bytes | None:
    async with db.connect("guard") as conn:
        row = await repo.get_action(conn, action_id, citizen_id)
    if row is None or row["evidence_enc"] is None:
        return None
    return crypto.decrypt(citizen_id, bytes(row["evidence_enc"]))


async def _execute_with_retry(row: dict[str, Any]) -> ActionResult:
    """FR-G-11 / NFR-G-04: повтор — один и только если форма точно не отправлена."""
    executor = EXECUTORS.get(row["type"])
    if executor is None:
        return ActionResult(ok=False, submitted=False, error="no_executor")
    req = ActionRequest(action_id=row["id"], citizen_id=row["citizen_id"], document_id=row["document_id"],
                        type=row["type"], idempotency_key=row["idempotency_key"])
    result = ActionResult(ok=False, submitted=False, error="not_started")
    for attempt in (1, 2):
        try:
            async with documents.session_provider().get(row["citizen_id"]) as session:
                result = await executor.execute(req, session)
        except NotImplementedError:
            return ActionResult(ok=False, submitted=False, error="executor_not_implemented")
        except Exception as e:  # неизвестно, ушла ли форма: считаем, что ушла — повтора нет
            log.exception("executor crashed", extra={"action_id": str(row["id"]), "attempt": attempt})
            return ActionResult(ok=False, submitted=True, error=f"executor_crashed: {type(e).__name__}")
        if result.ok or result.submitted:
            return result
        log.warning("executor failed before submit, attempt %d: %s", attempt, result.error)
    return result


async def run_next_action() -> bool:
    """Воркер: взять одно подтверждённое действие и исполнить. False — работы нет."""
    async with db.connect("guard") as conn:
        row = await repo.claim_action(conn, ActionStatus.confirmed)
        if row is None:
            return False
        row = await _transition(conn, row, ActionStatus.executing, actor=SYSTEM)
    result = await _execute_with_retry(row)
    now = datetime.now(UTC)
    async with db.connect("guard") as conn:
        current = await repo.get_action(conn, row["id"], for_update=True)
        if current is None or current["status"] != ActionStatus.executing:
            return True  # кто-то уже закрыл (sweeper) — не трогаем
        common = {"evidence_enc": result.evidence_enc, "submitted_at": now if result.submitted else None}
        if result.ok:
            await _transition(conn, current, ActionStatus.verifying, actor=SYSTEM, **common)
        else:
            await _transition(conn, current, ActionStatus.failed, actor=SYSTEM, **common,
                              result={"verified_status": None, "error": result.error})
            return True
    try:  # шаг 5: внеочередной опрос источника, ждём document.status_changed -> revoked
        await documents.request_refresh(row["document_id"])
    except Exception:
        log.exception("request_refresh failed", extra={"action_id": str(row["id"])})
    return True


async def sweep_actions() -> int:
    """Таймауты: код (2 мин) -> expired; нет подтверждения источника (120 с) -> failed; зависшее исполнение."""
    n = 0
    async with db.connect("guard") as conn:
        for row in await repo.claim_expired_codes(conn):
            await _transition(conn, row, ActionStatus.expired, actor=SYSTEM, confirm_code_hash=None)
            n += 1
        for status, after, error in ((ActionStatus.verifying, VERIFY_TIMEOUT, "not_confirmed_by_source"),
                                     (ActionStatus.executing, EXECUTING_STALE, "interrupted")):
            while (row := await repo.claim_action(conn, status, older_than_s=after.total_seconds())) is not None:
                await _transition(conn, row, ActionStatus.failed, actor=SYSTEM,
                                  result={"verified_status": None, "error": error})
                n += 1
    return n


async def _close_verified_actions(conn: AsyncConnection, event: Event, document_id: UUID | None) -> None:
    """§9: status_changed -> revoked закрывает действие в verifying: «Подтверждено источником»."""
    if event.type != "document.status_changed" or document_id is None or event.data.get("status_to") != "revoked":
        return
    for row in await repo.verifying_actions(conn, document_id):
        await _transition(conn, row, ActionStatus.done, actor=SYSTEM,
                          result={"verified_status": "revoked", "error": None})
