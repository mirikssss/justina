"""Статья -> чанки для поиска.

Единица — статья (или пункт регламента): она же единица цитирования, поэтому ссылка в ответе указывает ровно на
найденное. Каждый чанк начинается с «хлебных крошек» (акт > глава > статья), чтобы быть понятным без соседей.

Статья, которая не помещается в окно модели эмбеддингов, режется по границам абзацев (частей статьи); слишком
длинный абзац — по предложениям, а в крайнем случае по словам. Иначе хвост статьи не попадает в векторный поиск:
модель молча отбрасывает всё, что дальше её окна (у multilingual-e5-small это 512 токенов).
"""

import re
from collections.abc import Callable
from dataclasses import dataclass

Counter = Callable[[str], int]
_SENTENCE = re.compile(r"(?<=[.;:!?])\s+")


@dataclass
class Chunk:
    article_id: int
    lang: str
    part: int
    content: str


def header(a: dict) -> str:
    word = "Статья" if a["lang"] == "ru" else "modda"
    num = f"{word} {a['number']}" if a["lang"] == "ru" else f"{a['number']}-{word}"
    crumbs = " > ".join(a["path"])
    return f"{a['doc_title']}\n{crumbs}\n{num}. {a['title']}"


def _part_label(lang: str, i: int) -> str:
    return f" (ч. {i})" if lang == "ru" else f" ({i}-qism)"


def _pack(units: list[str], room: int, count: Counter, sep: str) -> list[str]:
    """Жадно склеиваем единицы, пока помещаются в room токенов."""
    out: list[str] = []
    buf = ""
    for u in units:
        candidate = f"{buf}{sep}{u}" if buf else u
        if buf and count(candidate) > room:
            out.append(buf)
            buf = u
        else:
            buf = candidate
    if buf:
        out.append(buf)
    return out


def _fit(text: str, room: int, count: Counter) -> list[str]:
    """Абзац -> куски не длиннее room: целиком, иначе по предложениям, иначе по словам."""
    if count(text) <= room:
        return [text]
    pieces: list[str] = []
    for sentence in _SENTENCE.split(text):
        if count(sentence) <= room:
            pieces.append(sentence)
        else:
            pieces.extend(_pack(sentence.split(" "), room, count, " "))
    return _pack(pieces, room, count, " ")


def chunk_article(a: dict, count: Counter | None = None, budget: int | None = None) -> list[Chunk]:
    """budget — сколько токенов модель эмбеддингов реально прочитает; count — как их считать."""
    if count is None or budget is None:
        from storozh.assistant.rag.retrieval import embeddings

        count = count or embeddings.count_tokens
        budget = budget or embeddings.chunk_token_budget()

    head = header(a)
    whole = f"{head}\n{a['body']}"
    if count(whole) <= budget:
        return [Chunk(a["id"], a["lang"], 0, whole)]

    room = budget - count(head + _part_label(a["lang"], 99) + "\n")
    units = [u for para in a["body"].split("\n") if para.strip() for u in _fit(para, room, count)]
    parts = _pack(units, room, count, "\n")
    return [Chunk(a["id"], a["lang"], i, f"{head}{_part_label(a['lang'], i + 1)}\n{p}") for i, p in enumerate(parts)]
