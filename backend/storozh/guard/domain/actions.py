"""Конечный автомат действия и правила кода подтверждения. Чистые функции без базы и сети.

Переходы только вперёд (FR-G-07); каждый переход сервис пишет в audit_log и action.updated.
Код (FR-G-08): 6 цифр, в базе — HMAC с секретом и id действия, 2 минуты, 3 попытки.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID


class ActionStatus(StrEnum):
    proposed = "proposed"
    awaiting_confirmation = "awaiting_confirmation"
    confirmed = "confirmed"
    executing = "executing"
    verifying = "verifying"
    done = "done"
    failed = "failed"
    expired = "expired"


_FLOW = [ActionStatus.proposed, ActionStatus.awaiting_confirmation, ActionStatus.confirmed,
         ActionStatus.executing, ActionStatus.verifying, ActionStatus.done]
TERMINAL = {ActionStatus.done, ActionStatus.failed, ActionStatus.expired}
PAST_CONFIRMATION = {ActionStatus.confirmed, ActionStatus.executing, ActionStatus.verifying, ActionStatus.done}

ACTION_TYPES = {"revoke_car_poa"}  # белый список (FR-G-10); исполнители — adapters/actions
CODE_TTL = timedelta(minutes=2)
MAX_ATTEMPTS = 3
VERIFY_TIMEOUT = timedelta(seconds=120)  # ждём подтверждения источника (UC-G3, шаг 5)
EXECUTING_STALE = timedelta(minutes=5)  # воркер упал посреди исполнения


def can_transition(src: ActionStatus, dst: ActionStatus) -> bool:
    if src in TERMINAL:
        return False
    if dst == ActionStatus.expired:  # истекает только неподтверждённое действие
        return src in (ActionStatus.proposed, ActionStatus.awaiting_confirmation)
    if dst == ActionStatus.failed:
        return True
    return _FLOW.index(dst) == _FLOW.index(src) + 1


def new_code() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def hash_code(key: bytes, action_id: UUID, code: str) -> str:
    """HMAC, а не голый sha256: 10^6 вариантов перебираются за доли секунды, без ключа — нет."""
    return hmac.new(key, f"{action_id}:{code}".encode(), hashlib.sha256).hexdigest()


def code_matches(key: bytes, action_id: UUID, code: str, stored_hash: str | None) -> bool:
    return stored_hash is not None and hmac.compare_digest(hash_code(key, action_id, code), stored_hash)


class Confirm(StrEnum):
    accept = "accept"  # код верный -> confirmed
    already = "already"  # уже подтверждено: повтор confirm не запускает второе исполнение (NFR-G-03)
    wrong = "wrong"  # неверный код, попытки ещё есть -> 400
    exhausted = "exhausted"  # попытки кончились -> expired, 429
    timeout = "timeout"  # 2 минуты прошли -> expired, 410
    closed = "closed"  # действие уже завершилось неудачей -> 409


def judge_confirm(status: ActionStatus, attempts: int, expires_at: datetime | None, now: datetime,
                  code_ok: bool) -> Confirm:
    if status in PAST_CONFIRMATION:
        return Confirm.already
    if status == ActionStatus.expired:
        return Confirm.exhausted if attempts >= MAX_ATTEMPTS else Confirm.timeout
    if status != ActionStatus.awaiting_confirmation:
        return Confirm.closed
    if attempts >= MAX_ATTEMPTS:
        return Confirm.exhausted
    if expires_at is None or now >= expires_at:
        return Confirm.timeout
    if code_ok:
        return Confirm.accept
    return Confirm.exhausted if attempts + 1 >= MAX_ATTEMPTS else Confirm.wrong
