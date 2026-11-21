"""HTTP-эндпоинты «Помощника». /assist/search и /assist/ask — рабочий RAG из прежнего прототипа."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from storozh.assistant import contract, service
from storozh.shared.auth import Citizen, current_citizen
from storozh.shared.contracts import Lang

router = APIRouter(prefix="/assist", tags=["assistant"], dependencies=[Depends(current_citizen)])


class AskIn(BaseModel):
    question: str


class ChatIn(BaseModel):
    document_id: UUID
    message: str = Field(min_length=1, max_length=2000)
    lang: Lang | None = None


@router.get("/documents/{document_id}/summary")
async def document_summary(document_id: UUID, lang: Lang | None = None, citizen: Citizen = Depends(current_citizen)):
    """200 — резюме текущей версии; 202 — ещё считается, придёт summary.ready в /stream."""
    try:
        body = await service.get_summary(document_id, citizen.id, (lang or Lang.uz).value)  # по умолчанию узбекский
    except LookupError as e:
        raise HTTPException(status_code=404, detail="document not found") from e
    if body is None:
        return JSONResponse({"status": "pending"}, status_code=202)
    return body


@router.post("/chat")
async def chat(body: ChatIn, citizen: Citizen = Depends(current_citizen)):
    """Ответ потоком SSE: event token (кусок текста), event citations (Citation[]), event done."""
    if not await service.owns_document(body.document_id, citizen.id):
        raise HTTPException(status_code=404, detail="document not found")
    from storozh.assistant.rag.corpus.text import detect_lang

    lang = body.lang or Lang(detect_lang(body.message))  # по умолчанию — язык вопроса
    return EventSourceResponse(service.chat_events(body.document_id, citizen.id, body.message, lang))


@router.get("/chat/{document_id}")
async def chat_history(document_id: UUID, citizen: Citizen = Depends(current_citizen)):
    if not await service.owns_document(document_id, citizen.id):
        raise HTTPException(status_code=404, detail="document not found")
    return await service.chat_history(document_id, citizen.id)


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
    """Вопрос без документа: тот же пайплайн, что у чата (переписывание -> поиск -> один вызов модели)."""
    from storozh.assistant import chat
    from storozh.assistant.llm.provider import get_llm
    from storozh.assistant.rag.corpus.text import detect_lang

    result = chat.ChatResult()
    async for _ in chat.answer_stream(get_llm(), None, body.question, Lang(detect_lang(body.question)), None, result):
        pass
    return {"answer": result.text, "citations": [c.model_dump() for c in result.citations]}


_contract_calls: dict[UUID, list[float]] = {}
CONTRACT_LIMIT, CONTRACT_WINDOW_S = 10, 3600


@router.post("/contract")
async def review_contract(body: contract.ContractIn, citizen: Citizen = Depends(current_citizen)):
    """Проверка договора перед подписанием: текст или PDF/DOCX/TXT в base64. Не чаще 10 раз в час на человека (стоимость модели)."""
    import time

    from storozh.assistant.llm.port import LLMError
    from storozh.assistant.llm.provider import get_llm

    now = time.monotonic()
    calls = [t for t in _contract_calls.get(citizen.id, []) if now - t < CONTRACT_WINDOW_S]
    if len(calls) >= CONTRACT_LIMIT:
        raise HTTPException(status_code=429, detail="too many contract checks, try later")
    _contract_calls[citizen.id] = [*calls, now]
    try:
        return await contract.review(get_llm(), body, body.lang or Lang.uz)
    except contract.ContractError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except LLMError as e:
        raise HTTPException(status_code=503, detail="assistant unavailable") from e
