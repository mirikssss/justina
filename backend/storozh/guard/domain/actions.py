"""Конечный автомат действия. Переходы только вперёд; каждый — в audit_log и событие action.updated."""

from enum import StrEnum


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


def can_transition(src: ActionStatus, dst: ActionStatus) -> bool:
    if src in TERMINAL:
        return False
    if dst in (ActionStatus.failed, ActionStatus.expired):
        return True
    return _FLOW.index(dst) == _FLOW.index(src) + 1
