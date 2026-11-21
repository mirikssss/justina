"""Ссылки на нормы: модель пишет метки [[code:number]], мы оставляем только найденные фрагменты (FR-A-07)."""

import re
from collections.abc import Iterable

from storozh.assistant.public import Citation
from storozh.assistant.rag.retrieval.service import Hit

CITE = re.compile(r"\[\[([a-z0-9]+):([\d-]+)\]\]")
_LOOSE = re.compile(r"\b([a-z][a-z0-9]*):(\d+(?:-\d+)*)\b")  # «notary:31» без скобок — в списке ссылок


def label(hit: Hit) -> str:
    return f"[[{hit.code}:{hit.number}]]"


def to_citation(hit: Hit, lang: str | None = None) -> Citation:
    """Подпись ссылки — на языке ответа, даже если статья есть только на узбекском."""
    from storozh.assistant.rag.corpus.service import BY_CODE

    lang = lang or hit.lang
    src = BY_CODE[hit.code]
    return Citation(act_title=src.name_uz if lang == "uz" else src.name_ru,
                    article=src.article_label(hit.number, lang), url=hit.url)


def resolve(texts: Iterable[str], hits: list[Hit], lang: str | None = None) -> tuple[list[Citation], list[str]]:
    """Метки из текстов -> ссылки по найденным фрагментам. Второе значение — выдуманные метки (вырезаны)."""
    by_key = {(h.code, h.number): h for h in hits}
    found: dict[tuple[str, str], Citation] = {}
    unknown: list[str] = []
    for text in texts:
        for code, number in CITE.findall(text) or _LOOSE.findall(text):
            hit = by_key.get((code, number))
            if hit is None:
                unknown.append(f"{code}:{number}")
            elif (code, number) not in found:
                found[(code, number)] = to_citation(hit, lang)
    return list(found.values()), unknown


def strip(text: str) -> str:
    """Убрать метки из текста для показа (ссылки отдаются отдельным списком)."""
    return re.sub(r"\s*\[\[[a-z0-9]+:[\d-]+\]\]", "", text).strip()
