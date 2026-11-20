import json
from pathlib import Path

from storozh.guard.domain.rules import RuleContext, Severity, evaluate
from storozh.shared.contracts import NormalizedDocument
from storozh.shared.events import Event

EX = Path(__file__).resolve().parents[3] / "contracts" / "examples"
DOC = NormalizedDocument.model_validate(json.loads((EX / "normalized_document.poa_car.json").read_text()))
CREATED = Event.model_validate(json.loads((EX / "event.document.created.json").read_text()))


def test_g1_fires_for_new_poa_as_principal():
    [draft] = evaluate(CREATED, DOC, RuleContext())
    assert draft.rule_id == "G1" and draft.severity == Severity.critical


def test_g1_silent_when_owner_is_agent():
    doc = DOC.model_copy(update={"owner_role": "agent"})
    assert [d for d in evaluate(CREATED, doc, RuleContext()) if d.rule_id == "G1"] == []
