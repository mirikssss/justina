"""Порт модели. Сейчас — внешний LLM API, в целевом состоянии — модель в центре данных в Узбекистане.

У модели нет инструментов для действий и доступа к базе (NFR-A-03): только текст на вход и на выход.
"""

from typing import Protocol


class LLM(Protocol):
    async def complete(self, system: str, user: str, *, max_tokens: int = 1024, timeout_s: float = 30) -> str: ...
