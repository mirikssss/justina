"""Контекст для модели: несколько запросов -> гибридный поиск -> общий список фрагментов (без инструментов у модели)."""

import asyncio

from storozh.assistant.rag.retrieval.service import Hit, in_lang, search
from storozh.shared.contracts import DocumentKind

RRF_K = 60


def _merge(results: list[list[Hit]], k: int) -> list[Hit]:
    """Лучшая находка каждого запроса гарантированно попадает в выдачу (иначе узбекоязычные регламенты
    вытесняются статьями ГК, которые находятся сразу несколькими русскими запросами), остальное — по RRF."""
    scores: dict[tuple[str, str], float] = {}
    best: dict[tuple[str, str], Hit] = {}
    for hits in results:
        for rank, h in enumerate(hits):
            key = (h.code, h.number)
            scores[key] = scores.get(key, 0.0) + 1.0 / (RRF_K + rank + 1)
            best.setdefault(key, h)
    picked = list(dict.fromkeys((hits[0].code, hits[0].number) for hits in results if hits))[:k]
    for key in sorted(scores, key=scores.get, reverse=True):
        if len(picked) >= k:
            break
        if key not in picked:
            picked.append(key)
    return [best[key] for key in picked]


async def retrieve(queries: list[str], kinds: list[DocumentKind] | None = None, k: int = 8,
                   lang: str | None = None) -> list[Hit]:
    """top-k статей по всем запросам (FR-A-03: фильтр актов по типу документа); lang — версия статей для ответа."""
    queries = [q for q in dict.fromkeys(q.strip() for q in queries) if q]
    results = await asyncio.gather(*(asyncio.to_thread(search, q, k=k, expand=False, kinds=kinds)
                                     for q in queries))
    merged = _merge(list(results), k)
    return await asyncio.to_thread(in_lang, merged, lang) if lang else merged


def norms_block(hits: list[Hit], max_chars: int = 2200) -> str:
    """Нормы для промпта: метка, акт, статья, текст (длинный текст обрезается с пометкой)."""
    parts = []
    for h in hits:
        text = h.text if len(h.text) <= max_chars else h.text[:max_chars] + " …[текст статьи сокращён]"
        parts.append(f"[[{h.code}:{h.number}]] {h.act_title}, {h.article}. {h.title}\n{text}")
    return "\n\n".join(parts)
