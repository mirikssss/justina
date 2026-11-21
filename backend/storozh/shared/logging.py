"""Логи в JSON с request_id; ПИНФЛ (14 цифр), телефоны +998 и токены маскируются до вывода (NFR-D-06, NFR-P-04)."""

import contextvars
import json
import logging
import re
from datetime import UTC, datetime

_PATTERNS = [
    (re.compile(r"\b\d{14}\b"), "<pinfl>"),
    (re.compile(r"\+?998[\s-]?\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}"), "<phone>"),
    (re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b"), "<tg-token>"),
]

request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
_STD = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


def mask(text: str) -> str:
    for rx, repl in _PATTERNS:
        text = rx.sub(repl, text)
    return text


class MaskingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return mask(super().format(record))


class JsonFormatter(logging.Formatter):
    """Одна строка JSON: time, level, logger, msg, request_id, exc и всё из extra=. Маска — по готовой строке."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {"time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
                 "level": record.levelname.lower(), "logger": record.name, "msg": record.getMessage(),
                 "request_id": request_id.get()}
        entry.update({k: v for k, v in record.__dict__.items() if k not in _STD and not k.startswith("_")})
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return mask(json.dumps(entry, ensure_ascii=False, default=str))


def setup(level: int = logging.INFO, as_json: bool = True) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter() if as_json else
                         MaskingFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=level, handlers=[handler], force=True)
