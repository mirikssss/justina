"""Разбор двуязычной страницы lex.uz в структуру: документ -> статьи (с путём, текстом, ссылками)."""

import re
from dataclasses import dataclass, field

from lxml import html as lxml_html

_REF = re.compile(r"/docs/(-?\d+)(?:\?[^#\"]*)?(?:#(-?\d+))?")
_ART_RU = re.compile(r"^\s*Статья\s+([\d]+(?:[-.]\d+)*)\s*\.?\s*(.*)$", re.S)
_ART_UZ = re.compile(r"^\s*([\d]+(?:[-.]\d+)*)\s*-\s*(?:modda|модда)\s*\.?\s*(.*)$", re.S | re.I)
# Постановления и регламенты: единица — пункт «12. …» внутри приложения «4-ILOVA» / «ПРИЛОЖЕНИЕ № 4»
_ITEM = re.compile(r"^\s*(\d+(?:-\d+)?)\.\s+(.*)$", re.S)
_TO_RESOLUTION = re.compile(r"qaror|қарор|постановлени", re.I)
_APPX = re.compile(r"(\d+)\s*-?\s*(?:ILOVA|ИЛОВА)|ПРИЛОЖЕНИЕ\s*№?\s*(\d+)", re.I)

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


def _blocks(container):
    """(класс, elem_id, текст, ссылки) непустых блоков верхнего уровня."""
    for block in container:
        cls = (block.get("class") or "").split()
        inner = block.find("./div[@id]")
        if not cls or inner is None:
            continue
        refs = _refs(inner)
        text = _text(inner)
        if text:
            yield cls[0], int(inner.get("id")), text, refs


def _short_title(text: str, limit: int = 110) -> str:
    first = re.split(r"(?<=[.;:])\s", text.replace("\n", " "), maxsplit=1)[0]
    return first if len(first) <= limit else first[:limit].rsplit(" ", 1)[0] + "…"


def _parse_items(container, lang: str) -> ParsedDoc:
    """Акт без статей: пункты постановления и его приложений (регламентов). Номер = «<приложение>-<пункт>»."""
    title, appx, appx_title, skip = "", 0, None, False
    stack: list[tuple[int, str]] = []
    items: list[Article] = []
    current: Article | None = None

    for kind, elem_id, text, refs in _blocks(container):
        if kind == "ACT_TITLE":
            title = text.replace("\n", " ")
        elif kind == "APPL_BANNER_LANDSCAPE_TITLE":
            # приложение к самому постановлению («…qaroriga 4-ILOVA») — разбираем; приложения к регламенту
            # (схемы, формы заявлений: «…reglamentiga ILOVA») — пропускаем
            if _TO_RESOLUTION.search(text):
                m = _APPX.search(text)
                appx, skip = (int(m.group(1) or m.group(2)) if m else appx + 1), False
            else:
                skip = True
            appx_title, stack, current = None, [], None
        elif skip:
            continue
        elif kind == "ACT_TITLE_APPL":
            appx_title = text.replace("\n", " ")
        elif kind == "ACT_FORM" and appx_title and current is None:
            appx_title = f"{appx_title} {text.lower()}"
        elif kind == "TEXT_HEADER_DEFAULT":
            level = _header_level(text)
            stack = [(lv, h) for lv, h in stack if lv < level] + [(level, re.sub(r"\.?\s*\n\s*", ". ", text))]
            current = None
        elif kind == "ACT_TEXT":
            m = _ITEM.match(text)
            if m:
                number = f"{appx}-{m.group(1)}" if appx else m.group(1)
                path = ([appx_title] if appx_title else []) + [h for _, h in stack]
                current = Article(elem_id=elem_id, number=number, title=_short_title(m.group(2)), path=path,
                                  paragraphs=[text], refs=list(refs))
                items.append(current)
            elif current is not None:
                current.paragraphs.append(text)
                current.refs.extend(refs)
        elif kind == "CHANGES_ORIGINS" and current is not None:
            current.amendments.append(text)

    # номера пунктов могут повториться (опечатки в источнике): оставляем первый
    seen, unique = set(), []
    for it in items:
        if it.number not in seen:
            seen.add(it.number)
            unique.append(it)
    return ParsedDoc(lang=lang, title=title, articles=unique)


def _parse_container(container, lang: str) -> ParsedDoc:
    if not any((b.get("class") or "").startswith("CLAUSE_DEFAULT") for b in container):
        return _parse_items(container, lang)
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
