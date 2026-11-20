"""Нормализация текста: узбекская кириллица -> латиница, апострофы, токены для FTS."""

import re

# Порядок важен: многобуквенные сочетания раньше одиночных.
_CYR2LAT = [
    ("ё", "yo"), ("ю", "yu"), ("я", "ya"), ("ш", "sh"), ("ч", "ch"), ("ц", "ts"),
    ("ў", "o'"), ("ғ", "g'"), ("қ", "q"), ("ҳ", "h"), ("ж", "j"), ("х", "x"),
    ("а", "a"), ("б", "b"), ("в", "v"), ("г", "g"), ("д", "d"), ("е", "e"),
    ("з", "z"), ("и", "i"), ("й", "y"), ("к", "k"), ("л", "l"), ("м", "m"),
    ("н", "n"), ("о", "o"), ("п", "p"), ("р", "r"), ("с", "s"), ("т", "t"),
    ("у", "u"), ("ф", "f"), ("ъ", "'"), ("ь", ""), ("э", "e"), ("ы", "i"), ("щ", "sh"),
]
_UZ_ONLY_CYR = set("ўғқҳ")
_APOS = re.compile(r"[ʻʼ‘’`´]")
_WORD = re.compile(r"[a-zа-яёўғқҳ0-9']+", re.IGNORECASE)

UZ_STEM_LEN = 6  # грубый «стеммер» для агглютинативного узбекского: префикс слова


def norm_apostrophes(s: str) -> str:
    return _APOS.sub("'", s)


def cyr_to_lat(s: str) -> str:
    out = []
    for ch in s:
        low = ch.lower()
        rep = next((lat for c, lat in _CYR2LAT if c == low), None)
        if rep is None:
            out.append(ch)
        else:
            out.append(rep.capitalize() if ch != low and rep else rep)
    return "".join(out)


def detect_lang(s: str) -> str:
    """ru | uz. Узбекская кириллица (ўғқҳ) или латиница с o'/g'/sh-маркерами -> uz."""
    low = norm_apostrophes(s.lower())
    if any(c in _UZ_ONLY_CYR for c in low):
        return "uz"
    cyr = sum("а" <= c <= "я" or c == "ё" for c in low)
    lat = sum("a" <= c <= "z" for c in low)
    return "ru" if cyr > lat else "uz"


def to_uz_latin(s: str) -> str:
    """Любой узбекский текст (кирилл/латин) -> латиница с ASCII-апострофом."""
    return norm_apostrophes(cyr_to_lat(norm_apostrophes(s)))


def uz_terms(s: str) -> list[str]:
    """Токены узбекского текста, обрезанные до префикса (shartnomaning -> shartn)."""
    words = _WORD.findall(to_uz_latin(s).lower())
    return [w.replace("'", "")[:UZ_STEM_LEN] for w in words if len(w) > 1]
