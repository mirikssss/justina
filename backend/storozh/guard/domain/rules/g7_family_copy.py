"""G7. Копия critical-тревоги родственнику, которому владелец выдал receive_alerts.

Оценивается на alert.created владельца отдельно для каждого родственника: ctx.family_consent=True,
если у этого родственника есть активное согласие со скоупом receive_alerts.
"""

from storozh.guard.domain.rules.base import AlertDraft, RuleContext, Severity, rule
from storozh.shared.contracts import NormalizedDocument
from storozh.shared.events import Event


@rule("G7")
def family_copy(event: Event, doc: NormalizedDocument | None, ctx: RuleContext) -> AlertDraft | None:
    if event.type != "alert.created" or not ctx.family_consent:
        return None
    if event.data.get("severity") != Severity.critical or event.data.get("rule_id") == "G7":
        return None
    return AlertDraft(
        rule_id="G7",
        rule_version=1,
        severity=Severity.critical,
        title="Важная тревога у вашего родственника",
        buttons=("open",),
    )
