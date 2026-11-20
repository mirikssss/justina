"""Вход, профиль и поток живых событий (SSE)."""

from fastapi import APIRouter, Depends

from storozh.shared.auth import Citizen, current_citizen

router = APIRouter(tags=["platform"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/auth/telegram/start")
async def auth_telegram_start():
    raise NotImplementedError("POST /auth/telegram/start")


@router.get("/auth/callback")
async def auth_callback(token: str):
    raise NotImplementedError("GET /auth/callback")


@router.post("/auth/logout", status_code=204)
async def auth_logout(citizen: Citizen = Depends(current_citizen)):
    raise NotImplementedError("POST /auth/logout")


@router.get("/me")
async def me(citizen: Citizen = Depends(current_citizen)):
    return {"id": str(citizen.id), "lang": citizen.lang, "display_name": "Dev Citizen"}


@router.get("/stream")
async def stream(citizen: Citizen = Depends(current_citizen)):
    """SSE: LISTEN storozh_outbox, фильтр по citizen_id; document.*, alert.created, action.updated, summary.ready."""
    raise NotImplementedError("GET /stream")
