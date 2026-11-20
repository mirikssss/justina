"""Разбор двуязычной страницы lex.uz в структуру: документ -> статьи (с путём, текстом, ссылками)."""

import re
from dataclasses import dataclass, field

from lxml import html as lxml_html

_REF = re.compile(r"/docs/(-?\d+)(?:\?[^#\"]*)?(?:#(-?\d+))?")
_ART_RU = re.compile(r"^\s*Статья\s+([\d]+(?:[-.]\d+)*)\s*\.?\s*(.*)$", re.S)
_ART_UZ = re.compile(r"^\s*([\d]+(?:[-.]\d+)*)\s*-\s*(?:modda|модда)\s*\.?\s*(.*)$", re.S | re.I)

# Уровни заголовков: чем меньше, тем выше в иерархии.
_HEADER_LEVELS = [
    (re.compile(r"^(часть|.*\bqism\b)", re.I), 0),
    (re.compile(r"^(подраздел|.*kichik bo.?lim)", re.I), 2),
    (re.compile(r"^(раздел|.*bo.?lim)", re.I), 1),
    (re.compile(r"^(глава|.*\bbob\b)", re.I), 3),
    (re.compile(r"^(§|параграф|.*paragraf)", re.I), 4),
]


@dataclass
class Ref:
    lex_id: int
    elem_id: int | None
    anchor: str


@dataclass
class Article:
    elem_id: int
    number: str
    title: str
    path: list[str]
    paragraphs: list[str] = field(default_factory=list)
    amendments: list[str] = field(default_factory=list)
    refs: list[Ref] = field(default_factory=list)

    @property
    def body(self) -> str:
        return "\n".join(self.paragraphs)


@dataclass
class ParsedDoc:
    lang: str
    title: str
    articles: list[Article]
    lex_id: int | None = None  # id языковой версии на lex.uz (у узбекской — отрицательный)


def _text(el) -> str:
    for br in el.iter("br"):
        br.tail = "\n" + (br.tail or "")
    for sup in el.iter("sup"):  # "Статья 12<sup>1</sup>" -> "Статья 12-1"
        sup.text = "-" + (sup.text or "")
    return re.sub(r"[ \t ]+", " ", el.text_content()).strip()


def _header_level(text: str) -> int:
    for rx, level in _HEADER_LEVELS:
        if rx.match(text):
            return level
    return 3


def _refs(el) -> list[Ref]:
    out = []
    for a in el.iter("a"):
        m = _REF.search(a.get("href", ""))
        if m:
            anchor = re.sub(r"\s+", " ", a.text_content()).strip()
            out.append(Ref(int(m.group(1)), int(m.group(2)) if m.group(2) else None, anchor))
    return out


def _parse_container(container, lang: str) -> ParsedDoc:
    title = ""
    stack: list[tuple[int, str]] = []  # (level, header)
    articles: list[Article] = []
    current: Article | None = None
    art_rx = _ART_RU if lang == "ru" else _ART_UZ

    for block in container:
        cls = (block.get("class") or "").split()
        if not cls:
            continue
        kind = cls[0]
        inner = block.find("./div[@id]")
        if inner is None:
            continue
        refs = _refs(inner)
        text = _text(inner)
        if not text:
            continue
        elem_id = int(inner.get("id"))

        if kind == "ACT_TITLE":
            title = text.replace("\n", " ")
        elif kind == "TEXT_HEADER_DEFAULT":
            header = re.sub(r"\.?\s*\n\s*", ". ", text)
            level = _header_level(text)
            stack = [(lv, h) for lv, h in stack if lv < level] + [(level, header)]
            current = None
        elif kind == "CLAUSE_DEFAULT":
            m = art_rx.match(text)
            if not m:
                current = None
                continue
            current = Article(
                elem_id=elem_id,
                number=m.group(1).replace(".", "-"),
                title=m.group(2).strip().replace("\n", " "),
                path=[h for _, h in stack],
            )
            articles.append(current)
        elif kind == "ACT_TEXT" and current is not None:
            current.paragraphs.append(text)
            current.refs.extend(refs)
        elif kind == "CHANGES_ORIGINS" and current is not None:
            current.amendments.append(text)

    return ParsedDoc(lang=lang, title=title, articles=articles)


def _self_doc_id(container) -> int | None:
    """id языковой версии: тот документ, на элементы которого ведут ссылки внутри самой страницы."""
    own = {el.get("id") for el in container.iter("div") if el.get("id")}
    votes: dict[int, int] = {}
    for a in container.iter("a"):
        m = _REF.search(a.get("href", ""))
        if m and m.group(2) and m.group(2) in own:
            votes[int(m.group(1))] = votes.get(int(m.group(1)), 0) + 1
    return max(votes, key=votes.get) if votes else None


def parse_bilingual(page: str, ru_lex_id: int) -> dict[str, ParsedDoc]:
    """Возвращает {"ru": ParsedDoc, "uz": ParsedDoc} (uz — если на странице есть узбекская колонка)."""
    root = lxml_html.fromstring(page)
    out = {}
    for lang, cls in (("ru", "lang1"), ("uz", "lang2")):
        found = root.xpath(f'//div[@class="{cls}" or starts-with(@class, "{cls} ")]//div[@id="divCont"]')
        if found:
            doc = _parse_container(found[0], lang)
            doc.lex_id = ru_lex_id if lang == "ru" else _self_doc_id(found[0])
            if doc.articles:
                out[lang] = doc
    return out
