"""Хеш версии документа = SHA-256 канонического JSON (ключи по алфавиту, без source_ref.url)."""

import hashlib
import json
from typing import Any

from pydantic import BaseModel


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def content_hash(doc: BaseModel | dict) -> str:
    data = doc.model_dump(mode="json") if isinstance(doc, BaseModel) else dict(doc)
    ref = data.get("source_ref")
    if isinstance(ref, dict):  # url может меняться (сессия, параметры), на содержание не влияет
        data["source_ref"] = {k: v for k, v in ref.items() if k != "url"}
    return hashlib.sha256(canonical_json(data).encode()).hexdigest()
