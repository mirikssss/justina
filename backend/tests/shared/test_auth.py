import uuid

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from storozh.shared import auth
from storozh.shared.config import settings


def _request(method="GET", cookie=None, origin=None) -> Request:
    headers = []
    if cookie:
        headers.append((b"cookie", f"{auth.SESSION_COOKIE}={cookie}".encode()))
    if origin:
        headers.append((b"origin", origin.encode()))
    return Request({"type": "http", "method": method, "headers": headers, "path": "/", "query_string": b""})


@pytest.fixture
def sessions(monkeypatch):
    cid = uuid.uuid4()
    valid = {auth.token_hash("good"): auth.Citizen(id=cid, lang="ru")}

    async def resolver(token_hash: str):
        return valid.get(token_hash)

    monkeypatch.setattr(auth, "_resolver", resolver)
    return cid


async def test_session_cookie_resolves_citizen(sessions):
    c = await auth.current_citizen(_request(cookie="good"))
    assert (c.id, c.lang) == (sessions, "ru")


async def test_no_session_in_demo_is_401(sessions, monkeypatch):
    monkeypatch.setattr(settings, "env", "demo")
    with pytest.raises(HTTPException) as e:
        await auth.current_citizen(_request(cookie="bad"))
    assert e.value.status_code == 401


async def test_dev_fallback_and_origin_check(sessions, monkeypatch):
    monkeypatch.setattr(settings, "env", "dev")
    assert (await auth.current_citizen(_request())).id == auth.DEV_CITIZEN_ID
    monkeypatch.setattr(settings, "public_web_url", "http://localhost:3000")
    with pytest.raises(HTTPException) as e:
        await auth.current_citizen(_request("POST", cookie="good", origin="https://evil.example"))
    assert e.value.status_code == 403
    assert (await auth.current_citizen(_request("POST", cookie="good", origin="http://localhost:3000"))).id == sessions
