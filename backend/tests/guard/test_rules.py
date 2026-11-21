import json
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from storozh.guard.domain.rules import DAILY_CHECK, RULES, RuleContext, Severity, evaluate
from storozh.shared.contracts import DocumentKind as K
from storozh.shared.contracts import DocumentStatus as S
from storozh.shared.contracts import NormalizedDocument
from storozh.shared.contracts import OwnerRole as R
from storozh.shared.events import Event

EX = Path(__file__).resolve().parents[3] / "contracts" / "examples"
DOC = NormalizedDocument.model_validate(json.loads((EX / "normalized_document.poa_car.json").read_text()))
CREATED = Event.model_validate(json.loads((EX / "event.document.created.json").read_text()))
STATUS_CHANGED = Event.model_validate(json.loads((EX / "event.document.status_changed.json").read_text()))
CITIZEN = CREATED.citizen_id
TODAY = date(2026, 11, 21)


def ev(type: str, data: dict, subject: str = DOC.uri) -> Event:
    # Event(...) вместо Event.new: так можно собрать и внутреннее guard.daily_check.
    return Event(type=type, schema=f"{type}/v1", producer="guard" if type.startswith(("alert", "guard")) else "documents",
                 subject=subject, citizen_id=CITIZEN, dedupe_key=str(uuid4()), data=data)


def fired(event: Event, doc: NormalizedDocument | None, ctx: RuleContext | None = None) -> dict[str, object]:
    return {d.rule_id: d for d in evaluate(event, doc, ctx or RuleContext())}


def test_all_seven_rules_registered():
    assert sorted(RULES) == [f"G{i}" for i in range(1, 8)]


# G1 ------------------------------------------------------------------------
def test_g1_fires_for_new_poa_as_principal():
    [draft] = evaluate(CREATED, DOC, RuleContext())
    assert draft.rule_id == "G1" and draft.severity == Severity.critical
    assert draft.buttons == ("not_me_revoke", "me")


def test_g1_fires_for_notarial_poa():
    assert "G1" in fired(CREATED, DOC.model_copy(update={"kind": K.poa_notarial}))


def test_g1_silent_when_owner_is_agent():
    doc = DOC.model_copy(update={"owner_role": R.agent})
    assert "G1" not in fired(CREATED, doc)


def test_g1_silent_on_changed_event():
    assert "G1" not in fired(ev("document.changed", {}), DOC)


# G2 ------------------------------------------------------------------------
NOTARIAL = DOC.model_copy(update={"kind": K.notarial_act, "owner_role": R.party})


def test_g2_fires_for_notarial_act_as_party():
    d = fired(CREATED, NOTARIAL)["G2"]
    assert d.severity == Severity.high and d.buttons == ("not_me_art31", "me")
    assert "G1" not in fired(CREATED, NOTARIAL)


def test_g2_silent_when_not_party_or_not_created():
    assert "G2" not in fired(CREATED, NOTARIAL.model_copy(update={"owner_role": R.principal}))
    assert "G2" not in fired(ev("document.changed", {}), NOTARIAL)


# G3 ------------------------------------------------------------------------
def test_g3_fires_on_status_changed():
    d = fired(STATUS_CHANGED, DOC)["G3"]
    assert d.severity == Severity.info and d.buttons == ("open",)


def test_g3_silent_when_status_same_or_other_event():
    same = ev("document.status_changed", {"status_from": "active", "status_to": "active"})
    assert "G3" not in fired(same, DOC)
    assert "G3" not in fired(CREATED, DOC)


# G4 ------------------------------------------------------------------------
def poa_until(days: int, **upd) -> NormalizedDocument:
    return DOC.model_copy(update={"status": S.active, "valid_until": TODAY + timedelta(days=days), **upd})


@pytest.mark.parametrize("days", [0, 1, 7])
def test_g4_fires_when_poa_expires_within_7_days(days):
    d = fired(ev(DAILY_CHECK, {}), poa_until(days), RuleContext(today=TODAY))["G4"]
    assert d.severity == Severity.info


@pytest.mark.parametrize("days", [-1, 8, 30])
def test_g4_silent_outside_window(days):
    assert "G4" not in fired(ev(DAILY_CHECK, {}), poa_until(days), RuleContext(today=TODAY))


def test_g4_silent_for_inactive_non_poa_or_without_daily_check():
    ctx = RuleContext(today=TODAY)
    assert "G4" not in fired(ev(DAILY_CHECK, {}), poa_until(3, status=S.revoked), ctx)
    assert "G4" not in fired(ev(DAILY_CHECK, {}), poa_until(3, kind=K.vehicle), ctx)
    assert "G4" not in fired(ev(DAILY_CHECK, {}), poa_until(3, valid_until=None), ctx)
    assert "G4" not in fired(ev(DAILY_CHECK, {}), poa_until(3), RuleContext())  # нет даты проверки
    assert "G4" not in fired(CREATED.model_copy(), poa_until(3), ctx)  # не суточная проверка


# G5 ------------------------------------------------------------------------
def test_g5_fires_on_disappeared():
    e = ev("document.disappeared", {"document_id": str(uuid4()), "last_version_no": 3, "missing_count": 2})
    assert fired(e, DOC)["G5"].severity == Severity.high
    assert "G5" not in fired(CREATED, DOC)


# G6 ------------------------------------------------------------------------
def test_g6_fires_on_session_expired_without_document():
    e = ev("source.session_expired", {"source": "mygov.car_poa"}, subject="source:mygov.car_poa")
    [d] = evaluate(e, None, RuleContext())
    assert d.rule_id == "G6" and d.severity == Severity.high and d.buttons == ("reconnect",)


def test_rules_that_need_document_are_silent_without_it():
    assert evaluate(CREATED, None, RuleContext()) == []


# G7 ------------------------------------------------------------------------
def alert_created(severity: str, rule_id: str = "G1") -> Event:
    return ev("alert.created", {"alert_id": str(uuid4()), "rule_id": rule_id, "severity": severity,
                                "document_id": str(uuid4()), "rule_version": 1}, subject=str(uuid4()))


def test_g7_copies_critical_alert_to_relative_with_receive_alerts():
    d = fired(alert_created("critical"), DOC, RuleContext(family_consent=True))["G7"]
    assert d.severity == Severity.critical and d.buttons == ("open",)


def test_g7_silent_without_consent_for_non_critical_and_for_copies():
    assert "G7" not in fired(alert_created("critical"), DOC, RuleContext())
    assert "G7" not in fired(alert_created("high"), DOC, RuleContext(family_consent=True))
    assert "G7" not in fired(alert_created("critical", rule_id="G7"), DOC, RuleContext(family_consent=True))
