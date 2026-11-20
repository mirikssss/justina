"""HTTP-эндпоинты «Документов». Пути и схемы — строго по contracts/openapi.yaml."""

from uuid import UUID

from fastapi import APIRouter, Depends

from storozh.documents import service
from storozh.shared.auth import Citizen, current_citizen, internal_request
from storozh.shared.contracts import SourceSnapshot

router = APIRouter(tags=["documents"])
internal = APIRouter(tags=["internal"], dependencies=[Depends(internal_request)])


@router.get("/documents")
async def list_documents(kind: str | None = None, status: str | None = None, cursor: str | None = None,
                         citizen: Citizen = Depends(current_citizen)):
    raise NotImplementedError("GET /documents")


@router.get("/documents/{document_id}")
async def get_document(document_id: UUID, citizen: Citizen = Depends(current_citizen)):
    raise NotImplementedError("GET /documents/{id}")


@router.get("/documents/{document_id}/versions")
async def list_versions(document_id: UUID, citizen: Citizen = Depends(current_citizen)):
    raise NotImplementedError("GET /documents/{id}/versions")


@router.get("/documents/{document_id}/versions/{version_no}/diff")
async def version_diff(document_id: UUID, version_no: int, citizen: Citizen = Depends(current_citizen)):
    raise NotImplementedError("GET /documents/{id}/versions/{n}/diff")


@router.get("/sources")
async def list_sources(citizen: Citizen = Depends(current_citizen)):
    raise NotImplementedError("GET /sources")


@internal.post("/internal/ingest/snapshots", status_code=202)
async def ingest_snapshot(snapshot: SourceSnapshot):
    return await service.ingest_snapshot(snapshot)


@internal.post("/internal/documents/{document_id}/refresh", status_code=202)
async def refresh(document_id: UUID):
    await service.request_refresh(document_id)
