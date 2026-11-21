import asyncio

import pytest

from storozh.assistant import chat
from storozh.assistant.llm.port import LLMError
from storozh.assistant.rag.retrieval.service import Hit
from storozh.shared.contracts import Lang, NormalizedDocument


def _hit(code: str, number: str) -> Hit:
    return Hit(code=code, number=number, title="t", lang="ru", text="текст нормы", url=f"https://lex.uz/{code}#{number}",
               article_id=1, path=[])


HITS = [_hit("gk1", "141"), _hit("epoa", "1-23")]

DOC = NormalizedDocument.model_validate({
    "uri": "uz:notarius:poa:1", "kind": "poa_car", "source": "mygov.car_poa", "title": "Доверенность на автомобиль",
    "status": "active", "owner_role": "principal", "parties": [{"role": "agent", "name_masked": "Б***р К."}],
    "source_ref": {"external_id": "1"},
})


class FakeLLM:
    model = "fake"

    def __init__(self, chunks: list[str], complete: str = "ok", delay: float = 0) -> None:
        self.chunks, self._complete, self.delay, self.seen = chunks, complete, delay, []

    async def complete_json(self, system, user, schema, **kw):
        self.seen.append(user)
        return {"queries": ["отмена доверенности", "ishonchnomani bekor qilish"]}

    async def complete(self, system, user, **kw):
        await asyncio.sleep(self.delay)
        return self._complete

    async def stream(self, system, messages, **kw):
        self.seen.append(messages[-1]["content"])
        for c in self.chunks:
            yield c


@pytest.fixture(autouse=True)
def fake_retrieve(monkeypatch):
    async def retrieve(queries, kinds=None, k=8, lang=None):
        return HITS

    monkeypatch.setattr(chat, "retrieve", retrieve)


def test_rewriter_handles_split_markers_and_drops_unknown():
    rw = chat.CitationRewriter(HITS)
    out = "".join(rw.feed(c) for c in ["Отменить можно [[gk", "1:141]] в любое время", " [[uk:1]] и [[epoa:1-2", "3]]."])
    out += rw.flush()
    assert out == "Отменить можно [1] в любое время  и [2]."
    assert [c.article for c in rw.citations()] == ["ст. 141", "п. 23 прил. 1"]


async def test_answer_stream_masks_pii_and_returns_citations():
    llm = FakeLLM(["Да, можно [[gk1:141]]", ". Также через my.gov.uz [[epoa:1-23]]."])
    result = chat.ChatResult()
    text = "".join([p async for p in chat.answer_stream(llm, DOC, "Мой ПИНФЛ 31234567890123, как отменить?",
                                                         Lang.ru, [], result)])
    assert text == "Да, можно [1]. Также через my.gov.uz [2]." == result.text
    assert len(result.citations) == 2
    assert all("31234567890123" not in s for s in llm.seen)  # ПИНФЛ не ушёл в модель


async def test_no_norms_means_honest_no_answer(monkeypatch):
    async def empty(queries, kinds=None, k=8, lang=None):
        return []

    monkeypatch.setattr(chat, "retrieve", empty)
    result = chat.ChatResult()
    out = "".join([p async for p in chat.answer_stream(FakeLLM([]), DOC, "Сколько стоит бензин?", Lang.ru, [], result)])
    assert out == chat.NO_ANSWER[Lang.ru] and result.citations == []


async def test_explain_alert_timeout_and_length(monkeypatch):
    monkeypatch.setattr(chat, "ALERT_TIMEOUT_S", 0.05)
    assert await chat.explain_alert(FakeLLM([], "x", delay=1), "G1", DOC, Lang.ru) is None
    long = await chat.explain_alert(FakeLLM([], "слово " * 100), "G1", DOC, Lang.ru)
    assert long is not None and len(long) <= chat.ALERT_MAX_CHARS

    class Broken(FakeLLM):
        async def complete(self, *a, **kw):
            raise LLMError("down")

    assert await chat.explain_alert(Broken([]), "G1", DOC, Lang.uz) is None
