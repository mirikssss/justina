"""Вход, профиль, поток живых событий (SSE) и журнал аудита."""

import asyncio
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response
from psycopg import AsyncConnection
from sse_starlette.sse import EventSourceResponse

from storozh.platform import service
from storozh.platform.service import SESSION_TTL, LoginError
from storozh.platform.stream_hub import hub
from storozh.shared import audit, db
from storozh.shared.auth import SESSION_COOKIE, Citizen, current_citizen

router = APIRouter(tags=["platform"])

STREAM_TYPES = {"document.created", "document.changed", "document.status_changed", "document.disappeared",
                "alert.created", "action.updated", "summary.ready"}
HEARTBEAT_S = 15
AUDIT_PAGE = 50


@router.get("/healthz")
async def healthz():
    return {"status": "ok"}


@router.post("/auth/telegram/start")
async def auth_telegram_start():
    return {"deep_link": await service.start_login()}


@router.get("/auth/callback")
async def auth_callback(token: str):
    try:
        session = await service.consume_login(token)
    except LoginError:
        return RedirectResponse("/login?error=expired", status_code=302)
    resp = RedirectResponse("/documents", status_code=302)
    resp.set_cookie(SESSION_COOKIE, session, max_age=int(SESSION_TTL.total_seconds()), path="/",
                    secure=True, httponly=True, samesite="strict")
    return resp


@router.post("/auth/logout", status_code=204)
async def auth_logout(request: Request, citizen: Citizen = Depends(current_citizen)):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        await service.logout(token, citizen.id)
    resp = Response(status_code=204)
    resp.delete_cookie(SESSION_COOKIE, path="/", secure=True, httponly=True, samesite="strict")
    return resp


@router.get("/me")
async def me(citizen: Citizen = Depends(current_citizen)):
    return await service.profile(citizen.id)


async def _events_after(conn: AsyncConnection, citizen_id, last_seq: int) -> list[dict]:
    cur = await conn.execute(
        "SELECT seq, type, payload FROM shared.outbox WHERE seq > %s AND citizen_id = %s AND type = ANY(%s) "
        "ORDER BY seq LIMIT 200",
        (last_seq, citizen_id, sorted(STREAM_TYPES)),
    )
    return await cur.fetchall()


@router.get("/stream")
async def stream(request: Request, citizen: Citizen = Depends(current_citizen)):
    """SSE: события гражданина; heartbeat 15 с; Last-Event-ID — догнать пропущенное.

    T5: один LISTEN на процесс (stream_hub) будит подписчика, события он читает из outbox через пул.
    """
    last_id = request.headers.get("last-event-id")

    async def events():
        wake = hub.subscribe(citizen.id)
        try:
            async with db.connect("platform") as conn:
                if last_id and last_id.isdigit():
                    last_seq = int(last_id)
                else:
                    cur = await conn.execute("SELECT coalesce(max(seq), 0) AS seq FROM shared.outbox")
                    last_seq = (await cur.fetchone())["seq"]
            while not await request.is_disconnected():
                try:
                    await asyncio.wait_for(wake.wait(), timeout=HEARTBEAT_S)
                except TimeoutError:
                    continue  # тишина: heartbeat шлёт sse-starlette, заодно проверяем отключение
                wake.clear()
                async with db.connect("platform") as conn:
                    rows = await _events_after(conn, citizen.id, last_seq)
                for row in rows:
                    last_seq = row["seq"]
                    yield {"id": str(row["seq"]), "event": row["type"], "data": json.dumps(row["payload"])}
        finally:
            hub.unsubscribe(citizen.id, wake)

    return EventSourceResponse(events(), ping=HEARTBEAT_S)


@router.get("/audit")
async def audit_list(cursor: str | None = None, citizen: Citizen = Depends(current_citizen)):
    before = int(cursor) if cursor and cursor.isdigit() else None
    async with db.connect("platform") as conn:
        cur = await conn.execute(
            "SELECT seq, actor, action, target, at, hash FROM shared.audit_log "
            "WHERE actor = %s AND (%s::bigint IS NULL OR seq < %s) ORDER BY seq DESC LIMIT %s",
            (f"citizen:{citizen.id}", before, before, AUDIT_PAGE + 1),
        )
        rows = await cur.fetchall()
    items = rows[:AUDIT_PAGE]
    next_cursor = str(items[-1]["seq"]) if len(rows) > AUDIT_PAGE else None
    return {"items": [{**r, "at": r["at"].isoformat()} for r in items], "next_cursor": next_cursor}


@router.get("/audit/verify")
async def audit_verify():
    async with db.connect("platform") as conn:
        broken = await audit.verify(conn)
    return {"ok": broken is None, "broken_seq": broken}



