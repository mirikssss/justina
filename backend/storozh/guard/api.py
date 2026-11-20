"""HTTP-эндпоинты «Сторожа» (/guard/*). Пути и схемы — строго по contracts/openapi.yaml."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel

from storozh.shared.auth import Citizen, current_citizen

router = APIRouter(prefix="/guard", tags=["guard"], dependencies=[Depends(current_citizen)])


class VerdictIn(BaseModel):
    verdict: Literal["me", "not_me"]


class ActionIn(BaseModel):
    document_id: UUID
    type: Literal["revoke_car_poa"]


class CodeIn(BaseModel):
    code: str


class DraftIn(BaseModel):
    document_id: UUID
    type: Literal["art31_postpone", "court_claim"]


class InviteIn(BaseModel):
    scopes: list[Literal["read_documents", "receive_alerts"]]


class AcceptIn(BaseModel):
    code: str


@router.get("/alerts")
async def list_alerts(status: str | None = None, cursor: str | None = None):
    raise NotImplementedError("GET /guard/alerts")


@router.post("/alerts/{alert_id}/verdict")
async def alert_verdict(alert_id: UUID, body: VerdictIn):
    raise NotImplementedError("POST /guard/alerts/{id}/verdict")


@router.get("/documents/{document_id}/alerts")
async def document_alerts(document_id: UUID):
    raise NotImplementedError("GET /guard/documents/{id}/alerts")


@router.post("/actions", status_code=201)
async def create_action(body: ActionIn, idempotency_key: str = Header(alias="Idempotency-Key"),
                        citizen: Citizen = Depends(current_citizen)):
    raise NotImplementedError("POST /guard/actions")


@router.post("/actions/{action_id}/confirm")
async def confirm_action(action_id: UUID, body: CodeIn):
    raise NotImplementedError("POST /guard/actions/{id}/confirm")


@router.get("/actions/{action_id}")
async def get_action(action_id: UUID):
    raise NotImplementedError("GET /guard/actions/{id}")


@router.get("/actions/{action_id}/evidence")
async def action_evidence(action_id: UUID):
    raise NotImplementedError("GET /guard/actions/{id}/evidence")


@router.post("/drafts")
async def create_draft(body: DraftIn):
    raise NotImplementedError("POST /guard/drafts")


@router.post("/telegram/link")
async def telegram_link():
    raise NotImplementedError("POST /guard/telegram/link")


@router.get("/family")
async def family():
    raise NotImplementedError("GET /guard/family")


@router.post("/consents/invite")
async def consent_invite(body: InviteIn):
    raise NotImplementedError("POST /guard/consents/invite")


@router.post("/consents/accept")
async def consent_accept(body: AcceptIn):
    raise NotImplementedError("POST /guard/consents/accept")


@router.delete("/consents/{consent_id}", status_code=204)
async def revoke_consent(consent_id: UUID):
    raise NotImplementedError("DELETE /guard/consents/{id}")
