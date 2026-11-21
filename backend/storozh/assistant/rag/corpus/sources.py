"""Какие акты загружаем (FR-A-01). code — короткий ключ, aliases — как их называют пользователи.

unit: "article" — акт делится на статьи («Статья 31»); "item" — постановление/регламент делится на пункты
приложений, номер пункта = «<приложение>-<пункт>» (например, 4-16 — пункт 16 приложения 4).
Регламенты № 613 и № 726 на lex.uz есть только на узбекском: русские вопросы находят их через мультиязычный поиск.
"""

from dataclasses import dataclass, field

from storozh.shared.contracts import DocumentKind


@dataclass(frozen=True)
class Source:
    code: str
    lex_id: int
    name_ru: str
    name_uz: str
    aliases: tuple[str, ...]
    unit: str = "article"
    kinds: frozenset[DocumentKind] = field(default_factory=frozenset)  # для каких документов акт главный

    def article_label(self, number: str, lang: str = "ru") -> str:
        """Как показывать ссылку: «ст. 31» или «п. 16 прил. 4»."""
        if self.unit == "item":
            appx, _, item = number.rpartition("-")
            if lang == "uz":
                return f"{appx}-ilova {item}-band" if appx else f"{item}-band"
            return f"п. {item} прил. {appx}" if appx else f"п. {item}"
        return f"{number}-modda" if lang == "uz" else f"ст. {number}"


_K = DocumentKind
_POA = frozenset({_K.poa_car, _K.poa_notarial})
_NOTARIAL = frozenset({_K.notarial_act, _K.poa_notarial, _K.poa_car, _K.ban, _K.real_estate_right, _K.vehicle})

SOURCES: list[Source] = [
    Source("notary", 57043, "Закон «О нотариате»", "«Notariat toʻgʻrisida»gi Qonun",
           ("о нотариате", "закон о нотариате", "notariat to'g'risida", "notariat"), kinds=_NOTARIAL),
    Source("epoa", -6672128, "Регламент электронной доверенности на автомобиль (ПКМ № 613)",
           "Avtomototransport vositasini boshqarish ishonchnomasini elektron rasmiylashtirish reglamenti (VMQ 613)",
           ("электронная доверенность", "доверенность на авто", "elektron ishonchnoma"), unit="item",
           kinds=frozenset({_K.poa_car, _K.vehicle})),
    Source("reg726", -5109530, "Регламенты нотариальных действий (ПКМ № 726)",
           "Notarial harakatlar maʼmuriy reglamentlari (VMQ 726)",
           ("регламент нотариальных действий", "726", "notarial harakatlar reglamenti"), unit="item",
           kinds=_NOTARIAL),
    Source("vakolat", -7946843, "Положение о платформе Vakolat.uz (ПКМ № 825)",
           "Vakolat.uz platformasi toʻgʻrisidagi nizom (VMQ 825)",
           ("vakolat", "vakolat.uz", "электронная доверенность vakolat"), unit="item", kinds=_POA),
    Source("gk1", 111181, "Гражданский кодекс (часть 1)", "Fuqarolik kodeksi (1-qism)",
           ("гк", "гражданский кодекс", "fk", "fuqarolik kodeksi"), kinds=_NOTARIAL),
    Source("gk2", 180552, "Гражданский кодекс (часть 2)", "Fuqarolik kodeksi (2-qism)",
           ("гк", "гражданский кодекс", "fk", "fuqarolik kodeksi"), kinds=_NOTARIAL),
]

BY_CODE = {s.code: s for s in SOURCES}


def codes_for_kinds(kinds: list[DocumentKind] | None) -> list[str] | None:
    """FR-A-03: фильтр актов по типу документа. None — искать по всему корпусу."""
    if not kinds:
        return None
    codes = [s.code for s in SOURCES if s.kinds & set(kinds)]
    return codes or None
