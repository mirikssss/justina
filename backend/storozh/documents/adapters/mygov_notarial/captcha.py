"""Арифметическая капча истории нотариальных действий.

Текст — вычисляем выражение; картинка — Tesseract. 3 неудачи подряд — статус ошибки источника и пауза.
"""

import re

_EXPR = re.compile(r"^\s*(\d+)\s*([+\-*xх×])\s*(\d+)\s*=?\s*\??\s*$")


def solve_text(expr: str) -> int:
    m = _EXPR.match(expr)
    if not m:
        raise ValueError(f"unsupported captcha: {expr!r}")
    a, op, b = int(m[1]), m[2], int(m[3])
    return a + b if op == "+" else a - b if op == "-" else a * b


def solve_image(png: bytes) -> int:
    raise NotImplementedError("captcha.solve_image (Tesseract): Разработчик 1")
