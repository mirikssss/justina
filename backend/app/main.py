from fastapi import FastAPI
from pydantic import BaseModel

from app.modules.reasoning import service as reasoning
from app.modules.retrieval import service as retrieval

app = FastAPI(title="Justina — legal RAG")


class AskIn(BaseModel):
    question: str


@app.get("/search")
def search(q: str, k: int = 8, rerank: bool | None = None):
    return [
        {"code": h.code, "number": h.number, "title": h.title, "lang": h.lang, "url": h.url,
         "score": h.score, "via": sorted(h.via), "path": h.path, "text": h.text,
         "related": [{"code": r.code, "number": r.number, "title": r.title, "url": r.url} for r in h.related]}
        for h in retrieval.search(q, k=k, rerank=rerank)
    ]


@app.post("/ask")
def ask(body: AskIn):
    a = reasoning.answer(body.question)
    return {"answer": a.text, "citations": [c.__dict__ for c in a.citations],
            "unverified": a.unverified, "tool_calls": a.tool_calls}
