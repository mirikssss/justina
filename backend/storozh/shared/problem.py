"""Ошибки в формате application/problem+json (RFC 9457) и X-Request-Id на всех ответах."""

import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from storozh.shared.logging import request_id

PROBLEM = "application/problem+json"


def problem(status: int, title: str, detail: str | None = None, type_: str = "about:blank") -> JSONResponse:
    body = {"type": type_, "title": title, "status": status}
    if detail:
        body["detail"] = detail
    return JSONResponse(body, status_code=status, media_type=PROBLEM)


def install(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def _http(request: Request, exc: HTTPException):
        return problem(exc.status_code, str(exc.detail))

    @app.exception_handler(NotImplementedError)
    async def _todo(request: Request, exc: NotImplementedError):
        return problem(501, "Not implemented yet", str(exc) or None)

    @app.middleware("http")
    async def _request_id(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        token = request_id.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id.reset(token)
        response.headers["X-Request-Id"] = rid
        return response
