"""Сводка, «поделиться» и доказательный пакет на живой базе."""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx

from storozh.documents import service
from storozh.main import app
from storozh.shared.auth import DEV_CITIZEN_ID
from storozh.shared.config import settings
from storozh.shared.contracts import NormalizedDocument, SourceSnapshot
from tests.integration.conftest import requires_db

pytestmark = requires_db
EX = Path(__file__).resolve().parents[3] / "contracts" / "examples" / "normalized_document.poa_car.json"


async def test_overview_share_and_revoke(monkeypatch):
    monkeypatch.setattr(settings, "env", "dev")
    uri = f"uz:notarius:poa:{uuid.uuid4().hex[:10]}"
    doc = NormalizedDocument.model_validate({**json.loads(EX.read_text()), "uri": uri})
    await service.ingest_snapshot(SourceSnapshot(snapshot_id=uuid.uuid4(), citizen_id=DEV_CITIZEN_ID, source="mygov.car_poa",
                                                 fetched_at=datetime.now(UTC), complete=False, documents=[doc]))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as c:
        ov = (await c.get("/documents/overview")).json()
        assert ov["total"] >= 1 and {"by_kind", "attention", "sources", "expiring"} <= ov.keys()

        items = (await c.get("/documents", params={"q": uri})).json()["items"]
        doc_id = items[0]["id"]
        share = (await c.post(f"/documents/{doc_id}/share")).json()
        token = share["url"].rsplit("/", 1)[1]

        shared = (await c.get(f"/public/shared/{token}")).json()  # без входа
        assert shared["document"]["uri"] == uri and "source_ref" not in shared["document"]
        await c.get(f"/public/shared/{token}")
        info = (await c.get(f"/documents/{doc_id}/shares")).json()
        assert info[0]["views"] == 2 and info[0]["active"]

        assert (await c.delete(f"/shares/{share['share_id']}")).status_code == 204
        assert (await c.get(f"/public/shared/{token}")).status_code == 404
        assert (await c.get("/public/shared/short")).status_code == 404
        assert (await c.post(f"/documents/{uuid.uuid4()}/share")).status_code == 404
