"""Маски персональных данных для NormalizedDocument (FR-D-06, NFR-D-05).

В payload попадают только маски и HMAC; полные значения — только в зашифрованном raw_enc.
"""

import re

_SPACES = re.compile(r"\s+")


def mask_word(word: str) -> str:
    """Бахтиёр -> Б***р."""
    word = word.strip()
    if len(word) <= 2:
        return word[:1] + "*"
    return f"{word[0]}***{word[-1]}"


def mask_name(full_name: str) -> str:
    """«Каримов Бахтиёр Алишерович» -> «Б***р К.» (имя маской, фамилия инициалом). Порядок ФИО — как в MyGov."""
    parts = [p for p in _SPACES.split(full_name.strip()) if p]
    if not parts:
        return ""
    if len(parts) == 1:
        return mask_word(parts[0])
    surname, name = parts[0], parts[1]
    return f"{mask_word(name)} {surname[0]}."


def mask_plate(plate: str) -> str:
    """«01 A 123 BC» / «01A123BC» -> «01 *** BC»: регион и последние два символа."""
    compact = _SPACES.sub("", plate).upper()
    if len(compact) < 4:
        return "***"
    return f"{compact[:2]} *** {compact[-2:]}"


def mask_number(number: str, keep: int = 3) -> str:
    """«2026-0001234» -> «2026-****234»: номер документа без середины."""
    number = number.strip()
    if len(number) <= keep + 2:
        return number
    head = number[:5] if "-" in number[:5] else number[:2]
    return head + "*" * max(len(number) - len(head) - keep, 3) + number[-keep:]
