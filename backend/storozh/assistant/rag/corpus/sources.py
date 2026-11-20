"""Какие акты загружаем. code — короткий ключ, aliases — как их называют пользователи."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    code: str
    lex_id: int
    name_ru: str
    aliases: tuple[str, ...]


SOURCES: list[Source] = [
    Source("konst", 6445147, "Конституция", ("конституция", "konstitutsiya")),
    Source("gk1", 111181, "Гражданский кодекс (часть 1)", ("гк", "гражданский кодекс", "fk", "fuqarolik kodeksi")),
    Source("gk2", 180552, "Гражданский кодекс (часть 2)", ("гк", "гражданский кодекс", "fk", "fuqarolik kodeksi")),
    Source("tk", 6257288, "Трудовой кодекс", ("тк", "трудовой кодекс", "mk", "mehnat kodeksi")),
    Source("sk", 104723, "Семейный кодекс", ("ск", "семейный кодекс", "ok", "oila kodeksi")),
    Source("zhk", 106134, "Жилищный кодекс", ("жк", "жилищный кодекс", "uy-joy kodeksi")),
    Source("koao", 97664, "Кодекс об административной ответственности", ("коао", "кодекс об административной ответственности", "majk", "ma'muriy javobgarlik")),
    Source("gpk", 3517334, "Гражданский процессуальный кодекс", ("гпк", "гражданский процессуальный кодекс", "fpk", "fuqarolik protsessual")),
    Source("uk", 111453, "Уголовный кодекс", ("ук", "уголовный кодекс", "jk", "jinoyat kodeksi")),
    Source("upk", 111460, "Уголовно-процессуальный кодекс", ("упк", "уголовно-процессуальный кодекс", "jpk", "jinoyat-protsessual")),
    Source("nk", 4674893, "Налоговый кодекс", ("нк", "налоговый кодекс", "soliq kodeksi")),
]

BY_CODE = {s.code: s for s in SOURCES}
