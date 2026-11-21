"""T12 / FR-G-12: POST /guard/drafts — ст. 31 и иск через assistant.draft_application."""

import uuid

import httpx
import pytest

from storozh.assistant.public import DraftRef
from storozh.guard import service
from storozh.shared import ratelimit


@pytest.fixture
def client(monkeypatch):
    from storozh.main import create_app

    calls = []

    async def draft(type, document_id, citizen_id):
        calls.append((type, document_id))
        if document_id == FOREIGN:
            raise LookupError(document_id)
        return DraftRef(draft_id=DRAFT, url=f"/assist/drafts/{DRAFT}")

    monkeypatch.setattr(service.assistant, "draft_application", draft)
    ratelimit.window.reset()
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app()), base_url="http://x"), calls


DRAFT, FOREIGN = uuid.uuid4(), uuid.uuid4()


async def test_art31_draft_returns_pdf_link(client):
    cl, calls = client
    doc = uuid.uuid4()
    r = await cl.post("/guard/drafts", json={"document_id": str(doc), "type": "art31_postpone"})
    assert r.status_code == 200 and r.json() == {"draft_id": str(DRAFT), "url": f"/assist/drafts/{DRAFT}"}
    assert calls == [("art31_postpone", doc)]


async def test_court_claim_and_foreign_document(client):
    cl, _ = client
    assert (await cl.post("/guard/drafts", json={"document_id": str(uuid.uuid4()),
                                                  "type": "court_claim"})).status_code == 200
    r = await cl.post("/guard/drafts", json={"document_id": str(FOREIGN), "type": "art31_postpone"})
    assert r.status_code == 404 and r.headers["content-type"].startswith("application/problem+json")


async def test_unknown_draft_type_rejected(client):
    cl, calls = client
    r = await cl.post("/guard/drafts", json={"document_id": str(uuid.uuid4()), "type": "something"})
    assert r.status_code == 422 and calls == []
