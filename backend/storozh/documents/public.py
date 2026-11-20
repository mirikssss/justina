"""Публичный интерфейс «Документов» для других контекстов. Меняется только по согласованию.

Сейчас — сигнатуры из ТЗ; реализации подключает Разработчик 1.
"""

from contextlib import AbstractAsyncContextManager
from typing import Protocol
from uuid import UUID

from storozh.documents.ports import BrowserSession
from storozh.shared.contracts import NormalizedDocument

__all__ = ["BrowserSession", "NormalizedDocument", "SessionProvider", "get_document", "request_refresh",
           "session_provider"]


class SessionProvider(Protocol):
    """Сессия выдаётся под pg_advisory_lock по аккаунту: опрос и отзыв никогда не идут параллельно.

        async with documents.public.session_provider().get(citizen_id) as session:
            ...
    """

    def get(self, citizen_id: UUID, provider: str = "oneid") -> AbstractAsyncContextManager[BrowserSession]: ...


async def get_document(document_id: UUID) -> NormalizedDocument:
    from storozh.documents import service

    return await service.get_document(document_id)


async def request_refresh(document_id: UUID) -> None:
    """Внеочередной опрос источника документа (после действия «Сторожа»)."""
    from storozh.documents import service

    await service.request_refresh(document_id)


def session_provider() -> SessionProvider:
    from storozh.documents import service

    return service.session_provider()
