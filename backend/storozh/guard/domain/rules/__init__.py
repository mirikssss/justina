"""Правила — чистые функции (event, document, context) -> AlertDraft | None с id, версией и тестом.

Новое правило: файл gN_*.py (g1_new_poa … g7_family_copy) с @rule("GN") + импорт ниже + тест в tests/guard/.
"""

from storozh.guard.domain.rules import g1_new_poa  # noqa: F401  регистрирует правило
from storozh.guard.domain.rules.base import RULES, AlertDraft, RuleContext, Severity, evaluate

__all__ = ["RULES", "AlertDraft", "RuleContext", "Severity", "evaluate"]
