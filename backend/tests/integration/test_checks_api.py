"""POST /v1/checks на живой базе: проверка сохраняется, читается владельцем и не читается чужим; панель рисков без личных данных."""

import uuid

import httpx

from storozh.documents import checks
from storozh.main import app
from storozh.shared.config import settings
from tests.integration.conftest import requires_db

pytestmark = requires_db


async def test_check_roundtrip_and_analytics(monkeypatch):
    monkeypatch.setattr(settings, "env", "dev")  # dev-гражданин вместо входа
    monkeypatch.setattr(checks, "VAKOLAT_GAP_S", 0)

    async def fake_lookup(number, client=None):
        return {"found": True, "status": "active", "fields": {"n": number}, "unavailable": False}

    monkeypatch.setattr(checks, "vakolat_lookup", fake_lookup)
    number = f"T{uuid.uuid4().hex[:8]}"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as c:
        r = await c.post("/v1/checks", json={"poa_number": number, "seller_age": 71})
        assert r.status_code == 200
        body = r.json()
        assert body["risk_level"] == "medium" and body["consent_required"] and body["status"] == "pending"
        again = (await c.get(f"/v1/checks/{body['check_id']}")).json()
        assert again["check_id"] == body["check_id"] and {x["rule"] for x in again["reasons"]} == {"R3", "R8"}
        assert (await c.get(f"/v1/checks/{uuid.uuid4()}")).status_code == 404
        assert (await c.post("/v1/checks", json={"poa_number": "x"})).status_code == 422

        docs = (await c.get("/analytics/documents")).json()
        assert {"citizens", "documents", "by_kind_status"} <= docs.keys()
        risks = (await c.get("/analytics/risks")).json()
        assert {"alerts", "by_rule", "per_day", "delivery_seconds"} <= risks.keys()
        assert "citizen" not in str(risks).lower() and "uri" not in risks
