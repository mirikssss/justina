"""G4. Действующая доверенность истекает через ≤ 7 дней. Срабатывает только на суточной проверке."""

from storozh.guard.domain.rules.base import DAILY_CHECK, EXPIRING_KINDS, AlertDraft, RuleContext, Severity, rule
from storozh.shared.contracts import DocumentStatus, NormalizedDocument
from storozh.shared.events import Event

WINDOW_DAYS = 7


@rule("G4")
def poa_expiring(event: Event, doc: NormalizedDocument | None, ctx: RuleContext) -> AlertDraft | None:
    if event.type != DAILY_CHECK or ctx.today is None or doc is None:
        return None
    if doc.kind not in EXPIRING_KINDS or doc.status != DocumentStatus.active or doc.valid_until is None:
        return None
    if not 0 <= (doc.valid_until - ctx.today).days <= WINDOW_DAYS:
        return None
    return AlertDraft(
        rule_id="G4",
        rule_version=1,
        severity=Severity.info,
        title="Срок документа скоро истекает" if doc.kind == "identity_document" else "Срок доверенности скоро истекает",
        buttons=("open",),
    )
