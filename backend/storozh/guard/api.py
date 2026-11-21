"""HTTP-эндпоинты «Сторожа» (/guard/*). Пути и схемы — строго по contracts/openapi.yaml."""

import base64
import binascii
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, Field

from storozh.guard import service
from storozh.shared.auth import Citizen, current_citizen
from storozh.shared.problem import problem

router = APIRouter(prefix="/guard", tags=["guard"], dependencies=[Depends(current_citizen)])


class VerdictIn(BaseModel):
    verdict: Literal["me", "not_me"]


class ActionIn(BaseModel):
    document_id: UUID
    type: Literal["revoke_car_poa"]


class CodeIn(BaseModel):
    code: str = Field(pattern=r"^[0-9]{6}$")


class DraftIn(BaseModel):
    document_id: UUID
    type: Literal["art31_postpone", "court_claim"]


class InviteIn(BaseModel):
    scopes: list[Literal["read_documents", "receive_alerts"]]


class AcceptIn(BaseModel):
    code: str


def _encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(f"o:{offset}".encode()).decode()


def _decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        kind, n = base64.urlsafe_b64decode(cursor.encode()).decode().split(":")
        if kind != "o" or int(n) < 0:
            raise ValueError
        return int(n)
    except (ValueError, binascii.Error, UnicodeDecodeError) as e:
        raise HTTPException(400, "bad cursor") from e


@router.get("/alerts")
async def list_alerts(status: Literal["new", "seen", "closed"] | None = None, cursor: str | None = None,
                      citizen: Citizen = Depends(current_citizen)):
    page = await service.list_alerts(citizen.id, status, _decode_cursor(cursor))
    nxt = page["next_offset"]
    return {"items": page["items"], "next_cursor": _encode_cursor(nxt) if nxt is not None else None}


@router.post("/alerts/{alert_id}/verdict")
async def alert_verdict(alert_id: UUID, body: VerdictIn, citizen: Citizen = Depends(current_citizen)):
    alert = await service.set_verdict(citizen.id, alert_id, body.verdict)
    if alert is None:
        raise HTTPException(404, "alert not found")
    return alert


@router.get("/documents/{document_id}/alerts")
async def document_alerts(document_id: UUID, citizen: Citizen = Depends(current_citizen)):
    return await service.document_alerts(citizen.id, document_id)


def _action_problem(e: service.ActionError) -> Response:
    resp = problem(e.status, e.title)
    if e.status == 429:
        resp.headers["Retry-After"] = "120"
    return resp


@router.post("/actions", status_code=201)
async def create_action(body: ActionIn, idempotency_key: str = Header(alias="Idempotency-Key", min_length=16),
                        citizen: Citizen = Depends(current_citizen)):
    try:
        return await service.create_action(citizen.id, body.document_id, body.type, idempotency_key)
    except service.ActionError as e:
        return _action_problem(e)


@router.post("/actions/{action_id}/confirm")
async def confirm_action(action_id: UUID, body: CodeIn, citizen: Citizen = Depends(current_citizen)):
    try:
        return await service.confirm_action(citizen.id, action_id, body.code)
    except service.ActionError as e:
        return _action_problem(e)


@router.get("/actions/{action_id}")
async def get_action(action_id: UUID, citizen: Citizen = Depends(current_citizen)):
    action = await service.get_action(citizen.id, action_id)
    if action is None:
        raise HTTPException(404, "action not found")
    return action


@router.get("/actions/{action_id}/evidence")
async def action_evidence(action_id: UUID, citizen: Citizen = Depends(current_citizen)):
    png = await service.action_evidence(citizen.id, action_id)
    if png is None:
        raise HTTPException(404, "no evidence")
    return Response(png, media_type="image/png", headers={"Cache-Control": "private, no-store"})


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
