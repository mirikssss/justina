"""G3. У документа сменился статус (отозван, истёк, исполнен и т. п.)."""

from storozh.guard.domain.rules.base import AlertDraft, RuleContext, Severity, rule
from storozh.shared.contracts import NormalizedDocument
from storozh.shared.events import Event


@rule("G3")
def status_changed(event: Event, doc: NormalizedDocument | None, ctx: RuleContext) -> AlertDraft | None:
    if event.type != "document.status_changed" or event.data.get("status_from") == event.data.get("status_to"):
        return None
    return AlertDraft(
        rule_id="G3",
        rule_version=1,
        severity=Severity.info,
        title="Изменился статус документа",
        buttons=("open",),
    )
