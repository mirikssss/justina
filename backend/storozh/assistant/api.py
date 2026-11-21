"""HTTP-эндпоинты «Помощника». /assist/search и /assist/ask — рабочий RAG из прежнего прототипа."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from storozh.shared.auth import Citizen, current_citizen

router = APIRouter(prefix="/assist", tags=["assistant"], dependencies=[Depends(current_citizen)])


class AskIn(BaseModel):
    question: str


class ChatIn(BaseModel):
    document_id: UUID
    message: str
    lang: str = "uz"


@router.get("/documents/{document_id}/summary")
async def document_summary(document_id: UUID, lang: str = "uz"):
    raise NotImplementedError("GET /assist/documents/{id}/summary")


@router.post("/chat")
async def chat(body: ChatIn):
    raise NotImplementedError("POST /assist/chat (SSE)")


@router.get("/chat/{document_id}")
async def chat_history(document_id: UUID):
    raise NotImplementedError("GET /assist/chat/{document_id}")


@router.get("/drafts/{draft_id}")
async def draft_pdf(draft_id: UUID, citizen: Citizen = Depends(current_citizen)):
    """PDF черновика заявления (ст. 31 или иск); только владельцу."""
    from storozh.assistant.drafts import service as drafts

    found = await drafts.get_pdf(draft_id, citizen.id)
    if found is None:
        raise HTTPException(status_code=404, detail="draft not found")
    draft_type, pdf = found
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{draft_type}-{draft_id}.pdf"'})


@router.get("/search")
async def search(q: str, k: int = 8, rerank: bool | None = None):
    from storozh.assistant.rag.retrieval import service as retrieval

    hits = await run_in_threadpool(retrieval.search, q, k=k, rerank=rerank)
    return [
        {"act_id": h.act_id, "act_title": h.act_title, "article": h.article,
         "code": h.code, "number": h.number, "title": h.title, "lang": h.lang, "url": h.url,
         "score": h.score, "via": sorted(h.via), "path": h.path, "text": h.text,
         "related": [{"code": r.code, "number": r.number, "title": r.title, "url": r.url} for r in h.related]}
        for h in hits
    ]


@router.post("/ask")
async def ask(body: AskIn):
    from storozh.assistant.llm import service as llm

    a = await run_in_threadpool(llm.answer, body.question)
    return {"answer": a.text, "citations": [c.__dict__ for c in a.citations],
            "unverified": a.unverified, "tool_calls": a.tool_calls}
