import logging
import uuid

import pytest

from storozh.assistant import summary
from storozh.assistant.llm.port import LLMError
from storozh.assistant.llm.provider import AnthropicLLM
from storozh.shared.contracts import Lang
from tests.assistant.test_chat import DOC, HITS


class FakeLLM:
    model = "fake"

    def __init__(self):
        self.user = ""

    async def complete_json(self, system, user, schema, **kw):
        self.user = user
        return {"what_is_it": "Доверенность на ваш автомобиль [[gk1:141]]", "counterparty_can": ["управлять"],
                "risks": ["продать машину"], "what_to_do": ["отозвать на my.gov.uz"],
                "citations": ["[[gk1:141]]", "[[uk:999]]"]}


async def test_summary_verifies_citations_and_marks_document_as_data(monkeypatch):
    async def retrieve(queries, kinds=None, k=8):
        assert kinds == [DOC.kind]  # FR-A-03: фильтр актов по типу документа
        return HITS

    monkeypatch.setattr(summary, "retrieve", retrieve)
    llm = FakeLLM()
    s = await summary.summarize(llm, DOC, Lang.ru, uuid.uuid4(), 1)
    assert s.what_is_it == "Доверенность на ваш автомобиль"          # метки убраны из текста
    assert [c.article for c in s.citations] == ["ст. 141"]           # выдуманная uk:999 вырезана
    assert "<document>" in llm.user and "<norms>" in llm.user


def test_provider_refuses_pii_and_logs_requests(caplog):
    llm = AnthropicLLM("claude-sonnet-5-5")
    with pytest.raises(LLMError):
        llm._request("sys", [{"role": "user", "content": "ПИНФЛ 31234567890123"}], max_tokens=10, effort="low",
                     think=False)
    with caplog.at_level(logging.INFO, logger="storozh.assistant.llm.requests"):
        kw = llm._request("sys", [{"role": "user", "content": "[PINFL_1] и [NAME_1]"}], max_tokens=10,
                          effort="low", think=False)
    assert kw["thinking"] == {"type": "between_tools"} and kw["fallbacks"] == "default"
    assert caplog.records and "31234567890123" not in caplog.text  # NFR-A-02: в логе запросов нет ПИНФЛ
