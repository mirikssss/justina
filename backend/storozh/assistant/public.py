"""Публичный интерфейс «Помощника» для других контекстов (Разработчик 2)."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from storozh.shared.contracts import Lang, NormalizedDocument

__all__ = ["Citation", "DraftRef", "DraftType", "Summary", "draft_application", "explain_alert", "summarize"]

DraftType = Literal["art31_postpone", "court_claim"]


class Citation(BaseModel):
    act_title: str
    article: str
    url: str


class Summary(BaseModel):
    """Структурированное резюме, проверенное Pydantic (FR-A-04)."""

    document_id: UUID
    version_no: int
    lang: Lang
    what_is_it: str
    counterparty_can: list[str]
    risks: list[str]
    what_to_do: list[str]
    citations: list[Citation]


class DraftRef(BaseModel):
    draft_id: UUID
    url: str


async def summarize(doc: NormalizedDocument, lang: Lang) -> Summary:
    raise NotImplementedError("assistant.summarize: Разработчик 2")


async def explain_alert(rule_id: str, doc: NormalizedDocument, lang: Lang) -> str | None:
    """1–2 предложения до 300 знаков за ≤ 5 с. None при ошибке или таймауте — «Сторож» отправит шаблон."""
    raise NotImplementedError("assistant.explain_alert: Разработчик 2")


async def draft_application(type: DraftType, document_id: UUID, citizen_id: UUID) -> DraftRef:
    """PDF заявления: реквизиты из документа, текст из шаблона юриста. ФИО и ПИНФЛ — только в PDF, не в модель."""
    raise NotImplementedError("assistant.draft_application: Разработчик 2")
