"""HTTP-эндпоинты «Документов». Пути и схемы — строго по contracts/openapi.yaml."""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from storozh.documents import service
from storozh.shared.auth import Citizen, current_citizen, internal_request
from storozh.shared.contracts import SourceSnapshot

router = APIRouter(tags=["documents"])
internal = APIRouter(tags=["internal"], dependencies=[Depends(internal_request)])


def _not_found(e: service.NotFound) -> HTTPException:
    return HTTPException(status_code=404, detail=f"not found: {e}")


@router.get("/documents")
async def list_documents(kind: str | None = None, status: str | None = None, q: str | None = None,
                         cursor: str | None = None, citizen: Citizen = Depends(current_citizen)):
    try:
        return await service.list_documents(citizen.id, kind=kind, status=status, q=q, cursor=cursor)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="bad cursor") from e


@router.get("/documents/{document_id}")
async def get_document(document_id: UUID, citizen: Citizen = Depends(current_citizen)):
    try:
        return await service.get_document_detail(document_id, citizen.id)
    except service.NotFound as e:
        raise _not_found(e) from e


@router.get("/documents/{document_id}/versions")
async def list_versions(document_id: UUID, citizen: Citizen = Depends(current_citizen)):
    try:
        return await service.list_versions(document_id, citizen.id)
    except service.NotFound as e:
        raise _not_found(e) from e


@router.get("/documents/{document_id}/versions/{version_no}/diff")
async def version_diff(document_id: UUID, version_no: int, citizen: Citizen = Depends(current_citizen)):
    try:
        return await service.version_diff(document_id, version_no, citizen.id)
    except service.NotFound as e:
        raise _not_found(e) from e


@router.get("/sources")
async def list_sources(citizen: Citizen = Depends(current_citizen)):
    return await service.list_sources(citizen.id)


@router.post("/sources/{source_id}/refresh", status_code=202)
async def refresh_source(source_id: str, citizen: Citizen = Depends(current_citizen)):
    """Внеочередной опрос источника, не чаще раза в 20 с."""
    try:
        await service.refresh_source(citizen.id, source_id)
    except service.NotFound as e:
        raise _not_found(e) from e
    except service.TooSoon as e:
        raise HTTPException(status_code=429, detail="refresh not more often than every 20 s") from e


@internal.post("/internal/ingest/snapshots", status_code=202)
async def ingest_snapshot(request: Request):
    # тело читаем сами: подпись X-Signature считается по сырым байтам (shared.auth.internal_request)
    snapshot = SourceSnapshot.model_validate(json.loads(await request.body()))
    return await service.ingest_snapshot(snapshot)


@internal.post("/internal/documents/{document_id}/refresh", status_code=202)
async def refresh(document_id: UUID):
    try:
        await service.request_refresh(document_id)
    except service.NotFound as e:
        raise _not_found(e) from e
