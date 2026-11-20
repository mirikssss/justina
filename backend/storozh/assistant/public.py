"""Публичный интерфейс «Помощника» для других контекстов."""

from dataclasses import dataclass

from storozh.shared.contracts import Lang, NormalizedDocument

__all__ = ["Citation", "Summary", "explain_alert", "summarize"]


@dataclass(frozen=True)
class Citation:
    act: str
    article: str
    url: str


@dataclass(frozen=True)
class Summary:
    what: str  # что это
    other_party_can: str  # что может другая сторона
    risks: str  # чем рисковано
    todo: str  # что делать
    citations: list[Citation]


async def summarize(doc: NormalizedDocument, lang: Lang) -> Summary:
    raise NotImplementedError("assistant.summarize: Разработчик 3")


async def explain_alert(rule_id: str, doc: NormalizedDocument, lang: Lang) -> str:
    """До 300 знаков, ответ до 5 с. Вызывающий сам ставит таймаут и шаблон на случай отказа."""
    raise NotImplementedError("assistant.explain_alert: Разработчик 3")
