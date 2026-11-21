"""Маскирование персональных данных до отправки в модель (FR-A-08, NFR-A-02).

Метки обратимы только на нашей стороне: mapping хранится у нас и нужен только для PDF, в модель не уходит.
Одно и то же значение получает одну и ту же метку, поэтому модель понимает, что «[NAME_1]» встречается дважды.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

_CYR = "А-ЯЁЎҚҒҲ"
_cyr = "а-яёўқғҳ"
_APOS = "'ʻʼ‘’`"

# Порядок важен: сначала длинные и однозначные шаблоны.
_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("PINFL", re.compile(r"(?<!\d)\d{14}(?!\d)")),
    ("PASSPORT", re.compile(r"\b[A-Z]{2}\s?\d{7}\b")),
    ("PHONE", re.compile(r"\+?998[\s-]?\(?\d{2}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}(?!\d)")),
    ("PLATE", re.compile(r"\b\d{2}\s?[A-Z]\s?\d{3}\s?[A-Z]{2}\b|\b\d{2}\s?\d{3}\s?[A-Z]{3}\b")),
    # ФИО с отчеством: «Каримов Азиз Ахмедович», «Karimov Aziz Axmedovich», «Karimov Aziz Axmed o‘g‘li»
    ("NAME", re.compile(
        rf"\b[{_CYR}][{_cyr}]+\s+[{_CYR}][{_cyr}]+\s+[{_CYR}][{_cyr}]+(?:ович|евич|ьич|овна|евна|ична|инична)\b"
        rf"|\b[A-Z][a-z{_APOS}]+\s+[A-Z][a-z{_APOS}]+\s+[A-Z][a-z{_APOS}]+(?:ovich|evich|ovna|evna)\b"
        rf"|\b[A-Z][a-z{_APOS}]+\s+[A-Z][a-z{_APOS}]+\s+[A-Z][a-z{_APOS}]+\s+(?:o[{_APOS}]?g[{_APOS}]?li|qizi)\b"
        rf"|\b[{_CYR}][{_cyr}]+\s+[{_CYR}][{_cyr}]+\s+[{_CYR}][{_cyr}]+\s+(?:ўғли|угли|қизи|кизи)\b"
    )),
    # Фамилия с инициалами: «Каримов А.А.», «Karimov A.A.»
    ("NAME", re.compile(rf"\b[{_CYR}A-Z][{_cyr}a-z{_APOS}]{{2,}}\s+[{_CYR}A-Z]\.\s?(?:[{_CYR}A-Z]\.)?")),
]

# Для проверки перед вызовом модели: то, что точно нельзя отправлять.
_HARD = [rx for name, rx in _RULES if name in {"PINFL", "PASSPORT", "PHONE"}]


@dataclass
class Masked:
    text: str
    mapping: dict[str, str] = field(default_factory=dict)  # метка -> исходное значение

    def unmask(self, text: str) -> str:
        for label, value in self.mapping.items():
            text = text.replace(label, value)
        return text


class _Labeler:
    def __init__(self) -> None:
        self.by_value: dict[str, str] = {}
        self.mapping: dict[str, str] = {}
        self.counts: dict[str, int] = {}

    def label(self, kind: str, value: str) -> str:
        key = re.sub(r"\s+", " ", value.strip())
        if key not in self.by_value:
            self.counts[kind] = self.counts.get(kind, 0) + 1
            lbl = f"[{kind}_{self.counts[kind]}]"
            self.by_value[key] = lbl
            self.mapping[lbl] = value
        return self.by_value[key]


def mask(text: str, names: Iterable[str] = ()) -> Masked:
    """ПИНФЛ (14 цифр), паспорт (AA1234567), телефон +998, госномер, ФИО -> [PINFL_1], [PHONE_1], ...

    names — известные имена сторон документа (маскируются точным совпадением, даже без отчества).
    """
    lab = _Labeler()
    for name in sorted({n.strip() for n in names if n and len(n.strip()) > 2}, key=len, reverse=True):
        text = re.sub(re.escape(name), lambda m: lab.label("NAME", m.group(0)), text)
    for kind, rx in _RULES:
        text = rx.sub(lambda m, k=kind: lab.label(k, m.group(0)), text)
    return Masked(text=text, mapping=lab.mapping)


def contains_hard_pii(text: str) -> bool:
    """ПИНФЛ, паспорт или телефон в тексте — такой запрос в модель не отправляем."""
    return any(rx.search(text) for rx in _HARD)
