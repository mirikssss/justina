"""Черновики заявлений: draft_application и выдача PDF владельцу."""

import asyncio
from uuid import UUID

from storozh.assistant.drafts import render, repo
from storozh.documents import public as documents
from storozh.platform import public as platform
from storozh.shared import audit, crypto, db

DRAFT_TYPES = ("art31_postpone", "court_claim")


async def create(draft_type: str, document_id: UUID, citizen_id: UUID) -> UUID:
    if draft_type not in DRAFT_TYPES:
        raise ValueError(f"unknown draft type {draft_type!r}")
    async with db.connect("assistant") as conn:
        if await repo.document_owner(conn, document_id) != citizen_id:
            raise LookupError(document_id)
    doc = await documents.get_document(document_id)
    applicant = await platform.citizen_profile(citizen_id) or {}
    lang = applicant.get("lang") or "uz"
    pdf = await asyncio.to_thread(render.render_pdf, draft_type, render.context(doc, applicant, lang))
    async with db.connect("assistant") as conn:
        draft_id = await repo.save_draft(conn, citizen_id=citizen_id, document_id=document_id,
                                         draft_type=draft_type, pdf_enc=crypto.encrypt(citizen_id, pdf))
        await audit.write(conn, actor=f"citizen:{citizen_id}", action=f"draft.{draft_type}", target=str(document_id))
    return draft_id


async def get_pdf(draft_id: UUID, citizen_id: UUID) -> tuple[str, bytes] | None:
    async with db.connect("assistant") as conn:
        row = await repo.get_draft(conn, draft_id, citizen_id)
    if row is None:
        return None
    return row["type"], crypto.decrypt(citizen_id, row["pdf_enc"])
