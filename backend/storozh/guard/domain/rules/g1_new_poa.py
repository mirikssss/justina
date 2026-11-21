"""G1. Новая доверенность, где владелец кабинета — доверитель. Образец для остальных правил."""

from storozh.guard.domain.rules.base import POA_KINDS, AlertDraft, RuleContext, Severity, rule
from storozh.shared.contracts import NormalizedDocument, OwnerRole
from storozh.shared.events import Event


@rule("G1")
def new_poa_as_principal(event: Event, doc: NormalizedDocument | None, ctx: RuleContext) -> AlertDraft | None:
    if doc is None or event.type != "document.created" or doc.kind not in POA_KINDS or doc.owner_role != OwnerRole.principal:
        return None
    return AlertDraft(
        rule_id="G1",
        rule_version=1,
        severity=Severity.critical,
        title="От вашего имени выдана доверенность",
        buttons=("not_me_revoke", "me"),
    )
