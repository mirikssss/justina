"""Порты контекста «Документы». Новый реестр = новая папка в adapters/, ядро не меняется."""

from dataclasses import dataclass, field
from typing import Any, Protocol

from storozh.shared.contracts import NormalizedDocument


@dataclass(frozen=True)
class RawRecord:
    """Запись как её отдал источник, до нормализации. Целиком уходит в document_versions.raw_enc."""

    external_id: str
    data: dict[str, Any]
    html: str | None = None


@dataclass
class BrowserSession:
    """Залогиненная сессия OneID: Playwright storage state + httpx-клиент с теми же cookie."""

    citizen_id: Any
    storage_state: dict[str, Any]
    extra: dict[str, Any] = field(default_factory=dict)


class SourceAdapter(Protocol):
    source_id: str  # "mygov.car_poa"
    poll_interval_s: int
    complete: bool  # отдаёт ли fetch весь список (тогда пропажа записи — событие)

    async def fetch(self, session: BrowserSession) -> list[RawRecord]: ...

    def normalize(self, raw: RawRecord) -> NormalizedDocument: ...
