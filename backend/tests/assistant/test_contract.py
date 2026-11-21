import base64
import io
import zipfile

import pytest

from storozh.assistant import contract
from storozh.assistant.contract import ContractError, ContractIn
from storozh.shared.contracts import Lang

TEXT = ("ДОГОВОР ПОДРЯДА. Заказчик Иванов, ПИНФЛ 12345678901234, тел. +998 90 123 45 67, поручает Подрядчику выполнить ремонт "
        "за 10 000 000 сум в срок до 1 декабря. Оплата 50% авансом. Подрядчик вправе изменить цену в одностороннем порядке. ") * 3


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def test_text_passthrough_and_empty():
    assert contract.extract_text(ContractIn(text="abc")) == "abc"
    with pytest.raises(ContractError):
        contract.extract_text(ContractIn(text="   "))


def test_docx_and_txt_extraction():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", "<w:document><w:p><w:t>Первый абзац</w:t></w:p><w:p><w:t>Второй</w:t></w:p></w:document>")
    out = contract.extract_text(ContractIn(filename="a.docx", content_base64=b64(buf.getvalue())))
    assert "Первый абзац" in out and "Второй" in out and "<w:" not in out
    assert contract.extract_text(ContractIn(filename="a.txt", content_base64=b64("привет".encode()))) == "привет"


@pytest.mark.parametrize("name,data", [("a.exe", b"x"), ("a.docx", b"not a zip"), ("a.txt", b"x" * 4_100_000)])
def test_bad_files_rejected(name, data):
    with pytest.raises(ContractError):
        contract.extract_text(ContractIn(filename=name, content_base64=b64(data)))


def test_prepare_masks_pii_and_truncates():
    text, truncated = contract.prepare(TEXT)
    assert "12345678901234" not in text and "123 45 67" not in text and not truncated
    _, truncated = contract.prepare("слово " * 10_000)
    assert truncated


class FakeLLM:
    model = "fake"

    def __init__(self):
        self.user = ""

    async def complete_json(self, system, user, schema, **kw):
        self.user = user
        return {"summary": "Договор подряда [[gk1:150]]", "obligations": ["Оплатить 50% авансом"],
                "risks": [{"level": "high", "text": "Подрядчик вправе менять цену в одностороннем порядке"}],
                "missing": ["Ответственность подрядчика"], "questions": ["Можно ли зафиксировать цену?"], "citations": []}


async def test_review_sends_masked_text_and_returns_structure(monkeypatch):
    async def fake_retrieve(queries, **kw):
        return []

    monkeypatch.setattr(contract, "retrieve", fake_retrieve)
    llm = FakeLLM()
    r = await contract.review(llm, ContractIn(text=TEXT), Lang.ru)
    assert "12345678901234" not in llm.user and "<contract>" in llm.user
    assert r.risks[0].level == "high" and "[[" not in r.summary and r.disclaimer.startswith("Это пояснение")


async def test_too_short_text_is_rejected():
    with pytest.raises(ContractError):
        await contract.review(FakeLLM(), ContractIn(text="коротко"), Lang.ru)
