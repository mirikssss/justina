from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

from storozh.shared.contracts import DocumentKind, NormalizedDocument
from storozh.shared.events import Event


class Severity(StrEnum):
    critical = "critical"
    high = "high"
    info = "info"


@dataclass(frozen=True)
class AlertDraft:
    rule_id: str
    rule_version: int
    severity: Severity
    title: str
    buttons: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuleContext:
    """Всё, что правилу нужно знать помимо события и документа (согласия семьи и т. п.)."""

    family_consent: bool = False  # G7: оцениваем для родственника, которому выдан receive_alerts
    today: date | None = None  # G4: дата суточной проверки (guard.daily_check)
    extra: dict = field(default_factory=dict)


# Внутреннее событие суточной проверки сроков (G4). В outbox не публикуется — его собирает планировщик guard.
DAILY_CHECK = "guard.daily_check"
POA_KINDS = frozenset({DocumentKind.poa_car, DocumentKind.poa_notarial})
# Документы со сроком действия, за которым следит G4: доверенности и паспорт/ID-карта
EXPIRING_KINDS = POA_KINDS | {DocumentKind.identity_document}


Rule = Callable[[Event, NormalizedDocument | None, RuleContext], AlertDraft | None]  # None: у события нет документа
RULES: dict[str, Rule] = {}


def rule(rule_id: str) -> Callable[[Rule], Rule]:
    def register(fn: Rule) -> Rule:
        if rule_id in RULES:
            raise ValueError(f"duplicate rule {rule_id}")
        RULES[rule_id] = fn
        return fn

    return register


def evaluate(event: Event, doc: NormalizedDocument | None, ctx: RuleContext) -> list[AlertDraft]:
    return [d for fn in RULES.values() if (d := fn(event, doc, ctx)) is not None]
