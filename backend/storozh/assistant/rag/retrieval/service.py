"""Публичный API модуля retrieval."""

from storozh.assistant.rag.retrieval import index
from storozh.assistant.rag.retrieval.search import Hit, search

__all__ = ["Hit", "search", "reindex"]


def reindex(codes: list[str] | None = None, embeddings: bool = True) -> dict:
    n = index.rebuild_chunks(codes)
    embedded = index.embed_missing() if embeddings else 0
    return {"chunks": n, "embedded": embedded}
