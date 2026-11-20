"""HTTP-эндпоинты «Помощника». /assist/search и /assist/ask — рабочий RAG из прежнего прототипа."""

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from storozh.shared.auth import current_citizen

router = APIRouter(prefix="/assist", tags=["assistant"], dependencies=[Depends(current_citizen)])


class AskIn(BaseModel):
    question: str


class ChatIn(BaseModel):
    document_id: UUID
    message: str


@router.get("/documents/{document_id}/summary")
async def document_summary(document_id: UUID, lang: str = "uz"):
    raise NotImplementedError("GET /assist/documents/{id}/summary")


@router.post("/chat")
async def chat(body: ChatIn):
    raise NotImplementedError("POST /assist/chat (SSE)")


@router.get("/search")
async def search(q: str, k: int = 8, rerank: bool | None = None):
    from storozh.assistant.rag.retrieval import service as retrieval

    hits = await run_in_threadpool(retrieval.search, q, k=k, rerank=rerank)
    return [
        {"code": h.code, "number": h.number, "title": h.title, "lang": h.lang, "url": h.url,
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
