"""Правила — чистые функции (event, document, context) -> AlertDraft | None с id, версией и тестом.

Новое правило: файл gN_*.py (g1_new_poa … g7_family_copy) с @rule("GN") + импорт ниже + тест в tests/guard/.
"""

from storozh.guard.domain.rules import (  # noqa: F401  импорт регистрирует правила
    g1_new_poa,
    g2_notarial_act,
    g3_status_changed,
    g4_poa_expiring,
    g5_disappeared,
    g6_session_expired,
    g7_family_copy,
)
from storozh.guard.domain.rules.base import DAILY_CHECK, RULES, AlertDraft, RuleContext, Severity, evaluate

__all__ = ["DAILY_CHECK", "RULES", "AlertDraft", "RuleContext", "Severity", "evaluate"]
