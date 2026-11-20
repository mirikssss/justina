"""Разбор запроса: язык, точные ссылки («ст. 123 ГК», «123-modda FK»), термы для полнотекста."""

import re
from dataclasses import dataclass, field

from storozh.assistant.rag.corpus.service import SOURCES
from storozh.assistant.rag.corpus.text import detect_lang, norm_apostrophes, to_uz_latin, uz_terms

_NUM_RU = re.compile(r"(?:\bст\.?|\bстать[яьиеюей]{1,2})\s*(\d+(?:-\d+)?)", re.I)
_NUM_UZ = re.compile(r"\b(\d+(?:-\d+)?)\s*-\s*modda", re.I)
_RU_WORD = re.compile(r"[а-яё]{3,}", re.I)


@dataclass
class ParsedQuery:
    text: str
    lang: str
    exact_keys: list[tuple[str, str]] = field(default_factory=list)  # (code, number)
    codes: list[str] = field(default_factory=list)  # кодексы, упомянутые в запросе

    @property
    def tsquery(self) -> tuple[str, str] | None:
        """(regconfig, tsquery) для to_tsquery; термы через OR — ранжирование решит ts_rank."""
        if self.lang == "ru":
            words = [w.lower() for w in _RU_WORD.findall(self.text)]
            return ("russian", " | ".join(dict.fromkeys(words))) if words else None
        terms = [t for t in uz_terms(self.text) if len(t) >= 3]
        return ("simple", " | ".join(dict.fromkeys(terms))) if terms else None


def _mentioned_codes(q: str) -> list[str]:
    low = norm_apostrophes(q.lower())
    lat = to_uz_latin(low)
    found = []
    for s in SOURCES:
        for alias in s.aliases:
            hay = low if re.search(r"[а-яё]", alias) else lat
            if re.search(rf"(?<![\w']){re.escape(alias)}(?![\w'])", hay):
                found.append(s.code)
                break
    return found


def parse(q: str) -> ParsedQuery:
    pq = ParsedQuery(text=q, lang=detect_lang(q))
    pq.codes = _mentioned_codes(q)
    nums = _NUM_RU.findall(q) + _NUM_UZ.findall(to_uz_latin(q))
    if nums and pq.codes:
        pq.exact_keys = [(c, n) for c in pq.codes for n in nums]
    return pq
