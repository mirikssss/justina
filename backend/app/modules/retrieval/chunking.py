"""Статья -> чанки. Каждый чанк несёт «хлебные крошки», чтобы быть понятным без соседей."""

from dataclasses import dataclass

MAX_CHARS = 3500


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


def chunk_article(a: dict) -> list[Chunk]:
    head = header(a)
    body = a["body"]
    if len(body) <= MAX_CHARS:
        return [Chunk(a["id"], a["lang"], 0, f"{head}\n{body}")]

    parts, buf = [], ""
    for para in body.split("\n"):
        if buf and len(buf) + len(para) > MAX_CHARS:
            parts.append(buf)
            buf = ""
        buf = f"{buf}\n{para}" if buf else para
    if buf:
        parts.append(buf)
    return [Chunk(a["id"], a["lang"], i, f"{head} (ч. {i + 1})\n{p}") for i, p in enumerate(parts)]
