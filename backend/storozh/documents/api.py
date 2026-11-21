"""HTTP-эндпоинты «Документов». Пути и схемы — строго по contracts/openapi.yaml."""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from storozh.documents import checks, features, service
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


@router.get("/documents/overview")
async def documents_overview(citizen: Citizen = Depends(current_citizen)):
    """Сводка: сколько документов, что истекает, что требует внимания, свежие изменения, здоровье источников."""
    return await features.overview(citizen.id)


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


# --- Проверка перед сделкой и кабинет нотариуса (00-project-overview, «API сторожа») ---


@router.post("/v1/checks")
async def create_check(body: checks.CheckRequest, citizen: Citizen = Depends(current_citizen)):
    """Синхронно: уровень риска, причины, нужно ли подтверждение доверителя, что не проверено (бюджет — до 2 с, реестр — до 8 с)."""
    return await checks.run_check(citizen.id, body)


@router.get("/v1/checks/{check_id}")
async def get_check(check_id: UUID, citizen: Citizen = Depends(current_citizen)):
    found = await checks.get_check(citizen.id, check_id)
    if found is None:
        raise HTTPException(status_code=404, detail="check not found")
    return found


@router.get("/analytics/documents")
async def analytics_documents(citizen: Citizen = Depends(current_citizen)):
    """Панель рисков: обезличенные агрегаты по документам (без личных данных)."""
    return await checks.document_stats()


# --- Поделиться документом (24 часа, журнал просмотров) и доказательный пакет ---


@router.post("/documents/{document_id}/share")
async def share_document(document_id: UUID, citizen: Citizen = Depends(current_citizen)):
    try:
        return await features.create_share(citizen.id, document_id)
    except service.NotFound as e:
        raise _not_found(e) from e


@router.get("/documents/{document_id}/shares")
async def document_shares(document_id: UUID, citizen: Citizen = Depends(current_citizen)):
    return await features.list_shares(citizen.id, document_id)


@router.delete("/shares/{share_id}", status_code=204)
async def revoke_share(share_id: UUID, citizen: Citizen = Depends(current_citizen)):
    if not await features.revoke_share(citizen.id, share_id):
        raise HTTPException(status_code=404, detail="share not found")


public = APIRouter(tags=["documents"])


@public.get("/public/shared/{token}")
async def shared_document(token: str):
    """Публично, без входа: замаскированный документ по временной ссылке. Каждый просмотр пишется в журнал."""
    found = await features.open_share(token) if 16 <= len(token) <= 64 else None
    if found is None:
        raise HTTPException(status_code=404, detail="link expired or not found")
    return found


@router.get("/documents/{document_id}/evidence.pdf")
async def document_evidence(document_id: UUID, citizen: Citizen = Depends(current_citizen)):
    """Доказательный пакет: все версии, хеши и что менялось — PDF для банка, нотариуса, суда."""
    try:
        pdf = await features.evidence_pdf(citizen.id, document_id)
    except service.NotFound as e:
        raise _not_found(e) from e
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="evidence-{document_id}.pdf"'})
