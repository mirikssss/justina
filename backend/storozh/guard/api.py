"""HTTP-эндпоинты «Сторожа». Пути и схемы — строго по contracts/openapi.yaml."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header

from storozh.shared.auth import Citizen, current_citizen

router = APIRouter(tags=["guard"], dependencies=[Depends(current_citizen)])


@router.get("/alerts")
async def list_alerts(cursor: str | None = None):
    raise NotImplementedError("GET /alerts")


@router.post("/alerts/{alert_id}/verdict")
async def alert_verdict(alert_id: UUID):
    raise NotImplementedError("POST /alerts/{id}/verdict")


@router.post("/actions", status_code=201)
async def create_action(idempotency_key: str = Header(alias="Idempotency-Key"),
                        citizen: Citizen = Depends(current_citizen)):
    raise NotImplementedError("POST /actions")


@router.post("/actions/{action_id}/confirm")
async def confirm_action(action_id: UUID):
    raise NotImplementedError("POST /actions/{id}/confirm")


@router.get("/actions/{action_id}")
async def get_action(action_id: UUID):
    raise NotImplementedError("GET /actions/{id}")


@router.get("/family")
async def family():
    raise NotImplementedError("GET /family")


@router.post("/consents", status_code=201)
async def create_consent():
    raise NotImplementedError("POST /consents")


@router.delete("/consents/{consent_id}", status_code=204)
async def revoke_consent(consent_id: UUID):
    raise NotImplementedError("DELETE /consents/{id}")


@router.get("/audit")
async def audit():
    raise NotImplementedError("GET /audit")


@router.get("/audit/verify")
async def audit_verify():
    raise NotImplementedError("GET /audit/verify")
