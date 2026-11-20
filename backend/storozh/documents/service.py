"""Сценарии «Документов»: приём снимков, версии, лента. Внутреннее — не импортировать снаружи."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from storozh.documents.ports import BrowserSession
from storozh.shared.contracts import NormalizedDocument, SourceSnapshot


async def ingest_snapshot(snapshot: SourceSnapshot) -> dict:
    """Проверка схемы, идемпотентность по snapshot_id, upsert по uri, новая версия только при другом хеше,
    события document.* в той же транзакции (shared.outbox.publish). disappeared — после двух полных снимков."""
    raise NotImplementedError("documents.ingest_snapshot: Разработчик 1")


async def get_document(document_id: UUID) -> NormalizedDocument:
    raise NotImplementedError("documents.get_document: Разработчик 1")


async def request_refresh(document_id: UUID) -> None:
    raise NotImplementedError("documents.request_refresh: Разработчик 1")


class _SessionProvider:
    @asynccontextmanager
    async def get(self, citizen_id: UUID, provider: str = "oneid") -> AsyncIterator[BrowserSession]:
        raise NotImplementedError("documents.SessionProvider: Разработчик 1")
        yield  # type: ignore[unreachable]


def session_provider() -> _SessionProvider:
    return _SessionProvider()
