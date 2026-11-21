"""G2. Новое нотариальное действие, где владелец кабинета — участник (сделка с его имуществом/от его имени)."""

from storozh.guard.domain.rules.base import AlertDraft, RuleContext, Severity, rule
from storozh.shared.contracts import DocumentKind, NormalizedDocument, OwnerRole
from storozh.shared.events import Event


@rule("G2")
def new_notarial_act_as_party(event: Event, doc: NormalizedDocument | None, ctx: RuleContext) -> AlertDraft | None:
    if doc is None or event.type != "document.created" or doc.kind != DocumentKind.notarial_act or doc.owner_role != OwnerRole.party:
        return None
    return AlertDraft(
        rule_id="G2",
        rule_version=1,
        severity=Severity.high,
        title="С вашим участием совершено нотариальное действие",
        buttons=("not_me_art31", "me"),
    )
