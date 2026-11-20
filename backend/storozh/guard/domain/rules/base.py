from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

from storozh.shared.contracts import NormalizedDocument
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

    family_consent: bool = False
    extra: dict = field(default_factory=dict)


Rule = Callable[[Event, NormalizedDocument, RuleContext], AlertDraft | None]
RULES: dict[str, Rule] = {}


def rule(rule_id: str) -> Callable[[Rule], Rule]:
    def register(fn: Rule) -> Rule:
        if rule_id in RULES:
            raise ValueError(f"duplicate rule {rule_id}")
        RULES[rule_id] = fn
        return fn

    return register


def evaluate(event: Event, doc: NormalizedDocument, ctx: RuleContext) -> list[AlertDraft]:
    return [d for fn in RULES.values() if (d := fn(event, doc, ctx)) is not None]
