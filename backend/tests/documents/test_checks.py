from datetime import date

import httpx
import pytest

from storozh.documents import checks
from storozh.documents.checks import CheckRequest, evaluate

TODAY = date(2026, 11, 21)
FOUND_ACTIVE = {"found": True, "status": "active", "fields": {}, "unavailable": False}
NOT_FOUND = {"found": False, "status": "unknown", "fields": {}, "unavailable": False}
DOWN = {"found": False, "status": "unknown", "fields": {}, "unavailable": True}


def req(**kw) -> CheckRequest:
    return CheckRequest(poa_number="2026-0001", **kw)


def rules(result) -> set[str]:
    return {r["rule"] for r in result["reasons"]}


def test_representative_needs_consent_medium_risk():
    r = evaluate(req(), FOUND_ACTIVE, None, TODAY)
    assert r["risk_level"] == "medium" and r["consent_required"] and rules(r) == {"R3"}


def test_owner_sells_himself_low_risk_no_consent():
    r = evaluate(req(acts_by_poa=False), FOUND_ACTIVE, None, TODAY)
    assert r["risk_level"] == "low" and not r["consent_required"] and r["reasons"] == []


def test_revoked_in_registry_blocks():
    r = evaluate(req(), {**FOUND_ACTIVE, "status": "revoked"}, None, TODAY)
    assert r["risk_level"] == "block" and "REV" in rules(r)


def test_revoked_in_justina_blocks_even_if_registry_silent():
    r = evaluate(req(), NOT_FOUND, {"status": "revoked", "issued_at": None, "holders": 1}, TODAY)
    assert r["risk_level"] == "block" and "OWN" in rules(r)


def test_young_poa_high_risk_from_request_or_own_data():
    assert "R4" in rules(evaluate(req(poa_issued_at=date(2026, 11, 1)), FOUND_ACTIVE, None, TODAY))
    own = {"status": "active", "issued_at": date(2026, 11, 10), "holders": 1}
    assert evaluate(req(), FOUND_ACTIVE, own, TODAY)["risk_level"] == "high"
    assert "R4" not in rules(evaluate(req(poa_issued_at=date(2026, 6, 1)), FOUND_ACTIVE, None, TODAY))


def test_not_found_without_own_data_is_high_and_unavailable_is_not_confused_with_it():
    assert evaluate(req(acts_by_poa=False), NOT_FOUND, None, TODAY)["risk_level"] == "high"
    down = evaluate(req(acts_by_poa=False), DOWN, None, TODAY)
    assert down["risk_level"] == "medium" and down["registry"]["unavailable"]


def test_age_rule_and_honest_not_checked_list():
    r = evaluate(req(acts_by_poa=False, seller_age=72), FOUND_ACTIVE, None, TODAY)
    assert "R8" in rules(r)
    assert {n["rule"] for n in r["not_checked"]} >= {"R1", "R2", "R5", "R6", "R7"}


def test_status_mapping():
    assert checks._status_for({"risk_level": "block", "consent_required": True}) == "denied"
    assert checks._status_for({"risk_level": "medium", "consent_required": True}) == "pending"
    assert checks._status_for({"risk_level": "low", "consent_required": False}) == "approved"


def test_poa_number_is_validated():
    with pytest.raises(ValueError):
        CheckRequest(poa_number="1; DROP TABLE")


@pytest.mark.parametrize("status_code,body,expected", [
    (422, {"status": {"code": "2013"}}, {"found": False, "unavailable": False}),
    (500, {}, {"found": False, "unavailable": True}),
])
async def test_vakolat_lookup_maps_registry_answers(monkeypatch, status_code, body, expected):
    monkeypatch.setattr(checks, "VAKOLAT_GAP_S", 0)

    def handler(request):
        return httpx.Response(status_code, json=body)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        got = await checks.vakolat_lookup("123456", client)
    assert got["found"] is expected["found"] and got["unavailable"] is expected["unavailable"]


async def test_registry_fields_are_masked(monkeypatch):
    monkeypatch.setattr(checks, "VAKOLAT_GAP_S", 0)
    payload = {"data": {"owner": {"pinfl": "12345678901234", "phone": "+998 90 123 45 67"}, "status": "Amalda"}}
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload))) as c:
        got = await checks.vakolat_lookup("123456", c)
    dumped = str(got["fields"])
    assert got["found"] and "12345678901234" not in dumped and "123 45 67" not in dumped


@pytest.mark.parametrize("valid,found", [(True, True), (False, False)])
async def test_vakolat_isvalid_is_the_real_format(monkeypatch, valid, found):
    monkeypatch.setattr(checks, "VAKOLAT_GAP_S", 0)
    seen = {}

    def handler(request):
        seen["path"] = request.url.path
        return httpx.Response(200, json={"data": {"isValid": valid}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        got = await checks.vakolat_lookup("2026-0001 234", c)
    assert got["found"] is found and got["unavailable"] is False
    assert seen["path"].endswith("/20260001234")  # разделители убраны: с дефисами реестр отвечает 500
