"""Белый список исполнителей. Исполнитель знает только типы отсюда."""

from storozh.guard.adapters.actions.mygov_revoke_car_poa.executor import RevokeCarPoaExecutor
from storozh.guard.ports import ActionExecutor

EXECUTORS: dict[str, ActionExecutor] = {e.action_type: e for e in [RevokeCarPoaExecutor()]}
