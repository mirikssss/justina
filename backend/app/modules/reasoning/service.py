"""Публичный API модуля reasoning."""

from app.modules.corpus.text import detect_lang
from app.modules.reasoning import agent
from app.modules.reasoning.agent import Answer, Citation

__all__ = ["Answer", "Citation", "answer"]


def answer(question: str, model: str | None = None, effort: str = "medium") -> Answer:
    return agent.answer(question, lang=detect_lang(question), model=model, effort=effort)
