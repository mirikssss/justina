"""Ссылки на нормы: модель пишет метки [[code:number]], мы оставляем только найденные фрагменты (FR-A-07)."""

import re
from collections.abc import Iterable

from storozh.assistant.public import Citation
from storozh.assistant.rag.retrieval.service import Hit

CITE = re.compile(r"\[\[([a-z0-9]+):([\d-]+)\]\]")


def label(hit: Hit) -> str:
    return f"[[{hit.code}:{hit.number}]]"


def to_citation(hit: Hit) -> Citation:
    return Citation(act_title=hit.act_title, article=hit.article, url=hit.url)


def resolve(texts: Iterable[str], hits: list[Hit]) -> tuple[list[Citation], list[str]]:
    """Метки из текстов -> ссылки по найденным фрагментам. Второе значение — выдуманные метки (вырезаны)."""
    by_key = {(h.code, h.number): h for h in hits}
    found: dict[tuple[str, str], Citation] = {}
    unknown: list[str] = []
    for text in texts:
        for code, number in CITE.findall(text):
            hit = by_key.get((code, number))
            if hit is None:
                unknown.append(f"{code}:{number}")
            elif (code, number) not in found:
                found[(code, number)] = to_citation(hit)
    return list(found.values()), unknown


def strip(text: str) -> str:
    """Убрать метки из текста для показа (ссылки отдаются отдельным списком)."""
    return re.sub(r"\s*\[\[[a-z0-9]+:[\d-]+\]\]", "", text).strip()
