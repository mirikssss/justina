"""Публичный API модуля retrieval."""

from storozh.assistant.rag.retrieval import index
from storozh.assistant.rag.retrieval.search import Hit, in_lang, search

__all__ = ["Hit", "in_lang", "search", "reindex"]


def reindex(codes: list[str] | None = None, embeddings: bool = True) -> dict:
    n = index.rebuild_chunks(codes)
    embedded = index.embed_missing() if embeddings else 0
    return {"chunks": n, "embedded": embedded}
