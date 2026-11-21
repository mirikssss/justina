"""G6. Сессия источника истекла — данные больше не обновляются, нужно переподключить."""

from storozh.guard.domain.rules.base import AlertDraft, RuleContext, Severity, rule
from storozh.shared.contracts import NormalizedDocument
from storozh.shared.events import Event


@rule("G6")
def session_expired(event: Event, doc: NormalizedDocument | None, ctx: RuleContext) -> AlertDraft | None:
    if event.type != "source.session_expired":
        return None
    return AlertDraft(
        rule_id="G6",
        rule_version=1,
        severity=Severity.high,
        title="Переподключите источник",
        buttons=("reconnect",),
    )
