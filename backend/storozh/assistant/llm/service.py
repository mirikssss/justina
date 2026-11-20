"""Публичный API ответа на вопрос со ссылками на статьи (агент на Claude)."""

from storozh.assistant.llm import agent
from storozh.assistant.llm.agent import Answer, Citation
from storozh.assistant.rag.corpus.text import detect_lang

__all__ = ["Answer", "Citation", "answer"]


def answer(question: str, model: str | None = None, effort: str = "medium") -> Answer:
    return agent.answer(question, lang=detect_lang(question), model=model, effort=effort)
