"""G5. Документ пропал из источника (несколько опросов подряд его нет)."""

from storozh.guard.domain.rules.base import AlertDraft, RuleContext, Severity, rule
from storozh.shared.contracts import NormalizedDocument
from storozh.shared.events import Event


@rule("G5")
def disappeared(event: Event, doc: NormalizedDocument | None, ctx: RuleContext) -> AlertDraft | None:
    if event.type != "document.disappeared":
        return None
    return AlertDraft(
        rule_id="G5",
        rule_version=1,
        severity=Severity.high,
        title="Документ исчез из источника",
        buttons=("open",),
    )
